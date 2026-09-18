"""
IP Intelligence & Device Fingerprinting Service
================================================
Enriches attacker IP addresses and User-Agents with:
- True source IP extraction (handles X-Forwarded-For, X-Real-IP, proxies)
- Network classification (Local LAN / Wi-Fi / Cloud Datacenter / Public Internet)
- Geolocation & ISP lookup (cached, async, with graceful offline fallbacks)
- Device & User-Agent fingerprinting (OS, Device Model, Browser/Tool)
"""
import ipaddress
import re
import time
import httpx
from typing import Optional

# In-memory cache for IP lookups to avoid rate limits
_GEO_CACHE: dict[str, dict] = {}


def extract_real_ip(headers: dict, client_host: str) -> str:
    """Extract real client IP considering proxy/forwarding headers."""
    headers_lower = {k.lower(): str(v) for k, v in headers.items()}
    
    # 1. X-Forwarded-For (first non-internal IP if possible, or first entry)
    xff = headers_lower.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]
            
    # 2. Other common proxy headers
    for header in ("x-real-ip", "cf-connecting-ip", "true-client-ip", "x-client-ip"):
        if header in headers_lower and headers_lower[header]:
            return headers_lower[header].strip()
            
    return client_host or "127.0.0.1"


def parse_user_agent(ua_string: str) -> dict:
    """Extract device type, operating system, and browser/tool from User-Agent."""
    ua = ua_string or "Unknown"
    ua_lower = ua.lower()

    # 1. Device Type
    device_type = "Desktop"
    device_icon = "💻"
    if any(m in ua_lower for m in ("iphone", "android", "mobile", "phone", "pixel", "samsung")):
        device_type = "Mobile Device"
        device_icon = "📱"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "Tablet"
        device_icon = "📲"
    elif any(b in ua_lower for b in ("python-requests", "curl", "flood-tool", "securityauditbot", "bot", "crawler", "postman", "http-client", "go-http-client")):
        device_type = "Automated Script / Bot"
        device_icon = "🤖"

    # 2. Operating System
    os_name = "Unknown OS"
    if "windows nt 10.0" in ua_lower or "windows nt 11.0" in ua_lower:
        os_name = "Windows 10/11"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "android" in ua_lower:
        match = re.search(r"android\s+([\d.]+)", ua_lower)
        os_name = f"Android {match.group(1)}" if match else "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower or "ios" in ua_lower:
        os_name = "iOS (Apple)"
    elif "macintosh" in ua_lower or "mac os x" in ua_lower:
        os_name = "macOS (Apple)"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "python" in ua_lower:
        os_name = "Python Runtime"

    # 3. Client / Browser / Tool
    client_name = "Unknown Client"
    if "edg/" in ua_lower:
        client_name = "Microsoft Edge"
    elif "chrome/" in ua_lower and "safari/" in ua_lower and "edg/" not in ua_lower:
        client_name = "Google Chrome"
    elif "safari/" in ua_lower and "chrome/" not in ua_lower:
        client_name = "Apple Safari"
    elif "firefox/" in ua_lower:
        client_name = "Mozilla Firefox"
    elif "python-requests" in ua_lower:
        client_name = "Python Requests Library"
    elif "curl" in ua_lower:
        client_name = "cURL CLI Tool"
    elif "flood-tool" in ua_lower:
        client_name = "Custom Flood Tester"
    elif "securityauditbot" in ua_lower:
        client_name = "AI Security Scanner"
    else:
        client_name = ua[:35] + ("..." if len(ua) > 35 else "")

    return {
        "raw": ua,
        "device_type": device_type,
        "device_icon": device_icon,
        "os": os_name,
        "client": client_name,
    }


async def get_ip_intelligence(ip: str, user_agent: str = "") -> dict:
    """Resolve full IP intelligence, network category, and device details."""
    device_info = parse_user_agent(user_agent)

    # Clean IP address
    ip_clean = ip.split(":")[0].strip() if ":" in ip and not ip.startswith("::") else ip.strip()

    # Check cache first
    if ip_clean in _GEO_CACHE:
        cached = dict(_GEO_CACHE[ip_clean])
        cached["device"] = device_info
        return cached

    intel = {
        "ip": ip_clean,
        "network_type": "Public Internet",
        "country": "Unknown",
        "country_code": "XX",
        "flag": "🌐",
        "city": "Unknown City",
        "region": "Unknown Region",
        "isp": "Unknown ISP / Cloud",
        "asn": "",
        "is_private": False,
        "is_datacenter": False,
        "device": device_info,
        "lookup_time": time.time(),
    }

    # Check for private / loopback IP ranges
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if ip_obj.is_loopback:
            intel.update({
                "network_type": "Loopback (Localhost)",
                "country": "Local System",
                "country_code": "LOCAL",
                "flag": "🏠",
                "city": "Local Machine",
                "region": "Loopback 127.0.0.1",
                "isp": "Internal Host Interface",
                "is_private": True,
            })
            _GEO_CACHE[ip_clean] = intel
            return intel

        if ip_obj.is_private:
            if ip_clean.startswith("192.168."):
                loc_name = "Wi-Fi / LAN Subnet (192.168.x.x)"
            elif ip_clean.startswith("10."):
                loc_name = "Enterprise LAN / VPN (10.x.x.x)"
            elif ip_clean.startswith("172."):
                loc_name = "Docker / Private LAN (172.x.x.x)"
            else:
                loc_name = "Private Network"

            intel.update({
                "network_type": "Local Network (Same Wi-Fi / LAN)",
                "country": "Local Network",
                "country_code": "LAN",
                "flag": "📡",
                "city": "Local Subnet Device",
                "region": loc_name,
                "isp": "Local Wi-Fi Network / Router",
                "is_private": True,
            })
            _GEO_CACHE[ip_clean] = intel
            return intel
    except ValueError:
        pass

    # For public IPs, try fast geo lookup with 1.5s timeout
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip_clean}?fields=status,country,countryCode,regionName,city,isp,org,as,mobile,proxy,hosting")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    country = data.get("country", "Unknown")
                    code = data.get("countryCode", "UN")
                    
                    # Compute emoji flag from country code
                    flag = "".join(chr(127397 + ord(c)) for c in code.upper()) if len(code) == 2 else "🌍"
                    
                    is_hosting = data.get("hosting", False) or "cloud" in str(data.get("isp", "")).lower() or "amazon" in str(data.get("isp", "")).lower() or "digitalocean" in str(data.get("isp", "")).lower()
                    
                    net_type = "Cloud Datacenter / Proxy" if is_hosting else ("Mobile Cellular" if data.get("mobile") else "Public Residential/Commercial")
                    
                    intel.update({
                        "network_type": net_type,
                        "country": country,
                        "country_code": code,
                        "flag": flag,
                        "city": data.get("city", "Unknown City"),
                        "region": data.get("regionName", ""),
                        "isp": data.get("isp") or data.get("org") or "Internet Service Provider",
                        "asn": data.get("as", ""),
                        "is_private": False,
                        "is_datacenter": is_hosting,
                    })
    except Exception:
        # Fallback for offline or rate-limited environments
        intel.update({
            "country": "External Public IP",
            "city": "Remote Host",
            "flag": "🌍",
            "isp": "Public Internet Gateway",
        })

    _GEO_CACHE[ip_clean] = intel
    return intel
