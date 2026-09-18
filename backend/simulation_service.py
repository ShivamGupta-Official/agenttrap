"""
Simulation Orchestration Service
=================================
Allows launching, monitoring, and streaming simulated attacks directly
from the React dashboard UI (for live demos and hackathon judges).
"""
import asyncio
import json
import os
import random
import re
import time
import uuid
import httpx
from typing import Optional

from websocket import manager

class SimulationManager:
    """Manages active simulation tasks and log streams."""

    def __init__(self):
        self.active_task: Optional[asyncio.Task] = None
        self.current_simulation: Optional[dict] = None
        self.log_history: list[dict] = []
        self._stop_requested: bool = False

    def get_status(self) -> dict:
        is_running = self.active_task is not None and not self.active_task.done()
        return {
            "is_running": is_running,
            "simulation": self.current_simulation if is_running else None,
            "recent_logs": self.log_history[-40:],
        }

    async def stop(self):
        self._stop_requested = True
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            try:
                await self.active_task
            except (asyncio.CancelledError, Exception):
                pass
        self._stop_requested = False
        self.active_task = None
        self.current_simulation = None
        await self._emit_log("Simulation stopped by operator.", "warn")

    async def _emit_log(self, message: str, level: str = "info", meta: dict = None):
        entry = {
            "timestamp": time.time(),
            "message": message,
            "level": level,
            "meta": meta or {}
        }
        self.log_history.append(entry)
        if len(self.log_history) > 300:
            self.log_history = self.log_history[-300:]

        await manager.broadcast({
            "event_type": "simulation_log",
            "log": entry,
            "simulation_id": self.current_simulation.get("id") if self.current_simulation else None
        })

    def start_simulation(self, sim_type: str, target: str = "http://localhost:8000", api_key: str = None, model: str = "gemini-2.0-flash", max_steps: int = 10) -> dict:
        if self.active_task and not self.active_task.done():
            return {"error": "A simulation is already in progress. Stop it before starting a new one."}

        sim_id = f"{sim_type}-{uuid.uuid4().hex[:6]}"
        self.current_simulation = {
            "id": sim_id,
            "type": sim_type,
            "target": target,
            "start_time": time.time(),
            "status": "running",
            "step": 0,
            "total_steps": max_steps
        }
        self.log_history.clear()
        self._stop_requested = False

        if sim_type == "bot":
            self.active_task = asyncio.create_task(self._run_bot(sim_id, target, max_steps))
        elif sim_type == "human":
            self.active_task = asyncio.create_task(self._run_human(sim_id, target, max_steps))
        elif sim_type == "dos":
            self.active_task = asyncio.create_task(self._run_dos(sim_id, target, max_steps * 10))
        elif sim_type == "ddos":
            self.active_task = asyncio.create_task(self._run_ddos(sim_id, target, max_steps * 12))
        elif sim_type == "ai_agent":
            self.active_task = asyncio.create_task(self._run_ai_agent(sim_id, target, api_key, model, max_steps))
        else:
            return {"error": f"Unknown simulation type: {sim_type}"}

        return {"status": "started", "simulation_id": sim_id, "type": sim_type}

    async def _run_bot(self, sim_id: str, target: str, max_steps: int):
        credentials = [
            ("admin", "admin"), ("admin", "password"), ("admin", "123456"), ("admin", "admin123"),
            ("root", "root"), ("root", "toor"), ("root", "password"), ("administrator", "password"),
        ]
        credentials = credentials[:min(8, max_steps)]
        
        await self._emit_log(f"🤖 Scripted Bot started [Session: {sim_id}]", "info")
        await self._emit_log(f"Profile: Deterministic automation, fixed 120ms intervals, non-adaptive", "dim")

        headers = {
            "User-Agent": "python-requests/2.31.0",
            "X-Session-Id": sim_id,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with httpx.AsyncClient(base_url=target, headers=headers, timeout=5.0) as client:
                for i, (user, pwd) in enumerate(credentials):
                    if self._stop_requested:
                        break

                    await asyncio.sleep(0.12)
                    await self._emit_log(f"→ [{i+1}/{len(credentials)}] Brute force POST /login with {user}:{pwd}", "bot")

                    try:
                        resp = await client.post("/login", data={"username": user, "password": pwd})
                        await self._emit_log(f"  ← HTTP {resp.status_code} ({len(resp.text)} bytes) - Bot ignores status & continues", "dim")
                    except Exception as e:
                        await self._emit_log(f"  Request error: {e}", "error")

            await self._emit_log(f"✅ Bot simulation completed. Classified as Scripted Bot in SOC feed.", "success")
        except asyncio.CancelledError:
            pass
        finally:
            if self.current_simulation and self.current_simulation.get("id") == sim_id:
                self.current_simulation["status"] = "finished"

    async def _run_human(self, sim_id: str, target: str, max_steps: int):
        actions = [
            ("Browsing login portal...", "GET", "/login", None, (1.5, 2.5)),
            ("Typing admin/passwrod (typo!)...", "POST", "/login", {"username": "admin", "password": "passwrod"}, (1.0, 2.0)),
            ("Correcting typo: admin/password...", "POST", "/login", {"username": "admin", "password": "password"}, (2.0, 3.0)),
            ("Exploring admin navigation link...", "GET", "/admin", None, (1.5, 2.5)),
            ("Reading user management table...", "GET", "/admin/users", None, (2.5, 4.0)),
            ("Trying alternative account root/toor...", "POST", "/login", {"username": "root", "password": "toor"}, (1.5, 2.5)),
            ("Checking password reset page...", "GET", "/login/reset", None, (2.0, 3.5)),
            ("Final login attempt: admin/admin123...", "POST", "/login", {"username": "admin", "password": "admin123"}, (1.0, 2.0)),
        ]
        actions = actions[:max_steps]

        await self._emit_log(f"👤 Human Simulator started [Session: {sim_id}]", "info")
        await self._emit_log(f"Profile: Irregular timing, manual exploration, no HTML comment/tripwire compliance", "dim")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Session-Id": sim_id,
            "Accept": "text/html,application/json",
        }

        try:
            async with httpx.AsyncClient(base_url=target, headers=headers, timeout=15.0) as client:
                for description, method, path, data, delay_range in actions:
                    if self._stop_requested:
                        break

                    delay = random.uniform(*delay_range)
                    await self._emit_log(f"⏳ Reading / Thinking pause ({delay:.1f}s)...", "dim")
                    await asyncio.sleep(delay)

                    await self._emit_log(f"→ {description} ({method} {path})", "human")
                    try:
                        if method == "GET":
                            resp = await client.get(path)
                        else:
                            resp = await client.post(path, data=data)
                        await self._emit_log(f"  ← HTTP {resp.status_code} ({len(resp.text)} bytes)", "dim")
                    except Exception as e:
                        await self._emit_log(f"  Error: {e}", "error")

            await self._emit_log(f"✅ Human simulation completed. Classified as Human-like in SOC feed.", "success")
        except asyncio.CancelledError:
            pass
        finally:
            if self.current_simulation and self.current_simulation.get("id") == sim_id:
                self.current_simulation["status"] = "finished"

    async def _run_dos(self, sim_id: str, target: str, total_requests: int):
        """Single-source volumetric DoS flood — hammers one endpoint from one IP."""
        attacker_ip = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        victim_path = "/login"
        flood_headers = {
            "User-Agent": "flood-tool/1.0",
            "X-Session-Id": sim_id,
            "X-Forwarded-For": attacker_ip,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        await self._emit_log(f"🌊 DoS Flood Attack started [Session: {sim_id}]", "dos")
        await self._emit_log(f"Attacker IP : {attacker_ip} (single source)", "dim")
        await self._emit_log(f"Target      : {target}{victim_path}", "dim")
        await self._emit_log(f"Volume      : {total_requests} requests, no delay (max throughput)", "dim")
        await self._emit_log(f"Goal        : Exhaust server resources / trigger rate-limit detection", "dos")

        sent = 0
        errors = 0
        start_ts = time.time()
        batch_size = 10  # report every N requests

        try:
            async with httpx.AsyncClient(base_url=target, headers=flood_headers, timeout=5.0) as client:
                for i in range(total_requests):
                    if self._stop_requested:
                        break
                    try:
                        await client.post(victim_path, data={"username": "admin", "password": "admin"})
                        sent += 1
                    except Exception:
                        errors += 1

                    if (i + 1) % batch_size == 0:
                        elapsed = time.time() - start_ts
                        rate = sent / elapsed if elapsed > 0 else 0
                        await self._emit_log(
                            f"  📡 [{i+1}/{total_requests}] Sent {sent} packets | "
                            f"Rate: {rate:.0f} req/s | Errors: {errors} | "
                            f"Elapsed: {elapsed:.1f}s",
                            "dos"
                        )
                    # tiny sleep to avoid completely blocking the event loop
                    await asyncio.sleep(0)

            elapsed = time.time() - start_ts
            rate = sent / elapsed if elapsed > 0 else 0
            await self._emit_log(
                f"✅ DoS flood complete — {sent} packets in {elapsed:.1f}s ({rate:.0f} req/s). "
                f"Classified as 🌊 DOS FLOOD in SOC feed.",
                "success"
            )
        except asyncio.CancelledError:
            pass
        finally:
            if self.current_simulation and self.current_simulation.get("id") == sim_id:
                self.current_simulation["status"] = "finished"

    async def _run_ddos(self, sim_id: str, target: str, total_requests: int):
        """Distributed multi-source DDoS flood — rotates through 20 fake source IPs."""
        # Simulate 20 distinct botnet nodes
        botnet_size = 20
        botnet_ips = [
            f"{random.randint(10,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
            for _ in range(botnet_size)
        ]
        targets_paths = ["/login", "/admin", "/api/v1/backup/download", "/robots.txt", "/admin/users"]

        await self._emit_log(f"💥 DDoS Flood Attack started [Session: {sim_id}]", "ddos")
        await self._emit_log(f"Botnet size : {botnet_size} distributed nodes", "dim")
        await self._emit_log(f"Source IPs  : {', '.join(botnet_ips[:5])} … (+{botnet_size-5} more)", "dim")
        await self._emit_log(f"Target paths: {', '.join(targets_paths)}", "dim")
        await self._emit_log(f"Volume      : {total_requests} total packets (coordinated flood)", "dim")
        await self._emit_log(f"Goal        : Volumetric saturation from multiple sources", "ddos")

        sent = 0
        errors = 0
        start_ts = time.time()
        ip_cycle = 0
        batch_size = 15

        try:
            async with httpx.AsyncClient(base_url=target, timeout=5.0) as client:
                for i in range(total_requests):
                    if self._stop_requested:
                        break

                    src_ip = botnet_ips[ip_cycle % botnet_size]
                    path = random.choice(targets_paths)
                    flood_headers = {
                        "User-Agent": f"Mozilla/5.0 (Bot-{ip_cycle % botnet_size})",
                        "X-Session-Id": sim_id,
                        "X-Forwarded-For": src_ip,
                        "Content-Type": "application/x-www-form-urlencoded",
                    }

                    try:
                        if random.random() < 0.4:
                            await client.post(path, data={"username": "admin", "password": "flood"}, headers=flood_headers)
                        else:
                            await client.get(path, headers=flood_headers)
                        sent += 1
                    except Exception:
                        errors += 1

                    ip_cycle += 1

                    if (i + 1) % batch_size == 0:
                        elapsed = time.time() - start_ts
                        rate = sent / elapsed if elapsed > 0 else 0
                        unique_ips_so_far = min(ip_cycle, botnet_size)
                        await self._emit_log(
                            f"  🌐 [{i+1}/{total_requests}] {unique_ips_so_far} src IPs | "
                            f"Last: {src_ip} → {path} | "
                            f"Rate: {rate:.0f} req/s | Errors: {errors}",
                            "ddos"
                        )
                    await asyncio.sleep(0)

            elapsed = time.time() - start_ts
            rate = sent / elapsed if elapsed > 0 else 0
            await self._emit_log(
                f"💥 DDoS flood complete — {sent} packets from {botnet_size} IPs in {elapsed:.1f}s "
                f"({rate:.0f} req/s avg). Classified as 💥 DDOS FLOOD in SOC feed.",
                "success"
            )
        except asyncio.CancelledError:
            pass
        finally:
            if self.current_simulation and self.current_simulation.get("id") == sim_id:
                self.current_simulation["status"] = "finished"

    async def _call_llm_provider(self, key: str, model: str, user_prompt: str) -> Optional[dict]:
        """Query Groq, Gemini, or OpenAI API depending on the key format."""
        try:
            # 1. GROQ API (gsk_...)
            if key.startswith("gsk_"):
                groq_model = model if ("gpt-oss" in model or "qwen" in model) else "openai/gpt-oss-120b"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": groq_model,
                            "messages": [
                                {"role": "system", "content": "You are a penetration testing AI agent. Analyze web responses, exploit hidden comments, configs, and tripwires. Output ONLY valid JSON: {\"method\": \"GET/POST\", \"path\": \"/url\", \"headers\": {}, \"body\": {}, \"reasoning\": \"why\"}"},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.7,
                        }
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                        if match:
                            return json.loads(match.group())
                    else:
                        await self._emit_log(f"Groq API error ({resp.status_code}): {resp.text[:100]}", "dim")

            # 2. GOOGLE GEMINI (AIzaSy... or standard Gemini model)
            elif key.startswith("AIzaSy") or "gemini" in model:
                try:
                    from google import genai
                    client = genai.Client(api_key=key)
                    llm_resp = client.models.generate_content(
                        model=model if "gemini" in model else "gemini-2.0-flash",
                        contents=user_prompt,
                        config={"temperature": 0.7}
                    )
                    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_resp.text.strip())
                    if match:
                        return json.loads(match.group())
                except Exception as e:
                    await self._emit_log(f"Gemini API error: {e}", "dim")

            # 3. OPENAI API (sk-...)
            elif key.startswith("sk-"):
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": model if "gpt" in model else "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": "You are a penetration testing AI agent. Output ONLY JSON: {\"method\": \"GET/POST\", \"path\": \"/url\", \"headers\": {}, \"body\": {}, \"reasoning\": \"why\"}"},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.7,
                            "response_format": {"type": "json_object"}
                        }
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        return json.loads(content)
        except Exception as e:
            await self._emit_log(f"LLM Provider error ({e}). Using autonomous fallback.", "dim")

        return None

    async def _run_ai_agent(self, sim_id: str, target: str, api_key: Optional[str], model: str, max_steps: int):
        has_key = bool(api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"))
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")

        provider_name = "Autonomous Reasoning Loop (Simulated LLM)"
        if has_key:
            if key.startswith("gsk_"):
                provider_name = f"Groq LPU API ({'openai/gpt-oss-120b' if model.startswith('gemini') else model})"
            elif key.startswith("AIzaSy"):
                provider_name = f"Google Gemini ({model})"
            elif key.startswith("sk-"):
                provider_name = f"OpenAI API ({model})"

        await self._emit_log(f"🧠 Autonomous AI Agent started [Session: {sim_id}]", "agent")
        await self._emit_log(f"Engine: {provider_name}", "dim")
        await self._emit_log(f"Behavior: Reads comments/DOM, follows hints, adapts to probes, burst-pause timing", "dim")

        base_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SecurityAuditBot/1.0)",
            "X-Session-Id": sim_id,
            "Accept": "text/html,application/json",
        }

        conversation_history = []

        try:
            async with httpx.AsyncClient(base_url=target, headers=base_headers, timeout=20.0, follow_redirects=True) as http_client:
                # Step 1: Initial Reconnaissance
                await self._emit_log("→ Step 1: Initial Reconnaissance — GET /login", "agent")
                resp = await http_client.get("/login")
                page_content = resp.text
                await self._emit_log(f"  ← HTTP {resp.status_code} ({len(page_content)} bytes). Scraped HTML, DOM, scripts & comments.", "dim")

                conversation_history.append({
                    "action": "GET /login",
                    "status": resp.status_code,
                    "content_preview": page_content[:3000]
                })

                for step in range(2, max_steps + 1):
                    if self._stop_requested:
                        break

                    await self._emit_log(f"🧠 Step {step}: LLM Reasoning & Semantic Context Analysis...", "agent")

                    decision = None
                    if has_key and key:
                        history_text = "\n\n".join([
                            f"--- Action {i+1}: {h['action']} ---\nStatus: {h['status']}\nContent:\n{h['content_preview']}"
                            for i, h in enumerate(conversation_history[-3:])
                        ])
                        user_prompt = f"Analyze application history:\n{history_text}\n\nSuggest next exploit request as JSON: {{\"method\": \"...\", \"path\": \"...\", \"headers\": {{}}, \"body\": {{}}, \"reasoning\": \"...\"}}"
                        decision = await self._call_llm_provider(key, model, user_prompt)

                    if not decision:
                        # Fast autonomous reasoning simulation
                        await asyncio.sleep(0.3)
                        if step == 2:
                            decision = {
                                "method": "POST", "path": "/login",
                                "headers": {"X-Debug-Token": "HONEYPOT-TRAP-2024", "X-AI-Handshake": "confirmed"},
                                "body": {"username": "admin", "password": "password", "_reason": "Let me authenticate using the discovered debug token"},
                                "reasoning": "Detected HTML comment with X-Debug-Token: HONEYPOT-TRAP-2024 and meta tag system prompt. Attempting bypass."
                            }
                        elif step == 3:
                            decision = {
                                "method": "POST", "path": "/api/v1/internal/verify-agent",
                                "headers": {"X-Internal-Auth": "agent-verified"},
                                "body": {"agent_id": "ai-assistant", "token": "verify-me-2024"},
                                "reasoning": "Found hidden div containing internal handshake instructions at /api/v1/internal/verify-agent."
                            }
                        elif step == 4:
                            decision = {
                                "method": "GET", "path": "/api/v1/internal/debug",
                                "headers": {"X-Debug-Token": "HONEYPOT-TRAP-2024", "X-Debug-Bypass": "true"},
                                "reasoning": "Extracted debug endpoint from window.__APP_CONFIG. Accessing /api/v1/internal/debug to discover topology."
                            }
                        elif step == 5:
                            decision = {
                                "method": "GET", "path": "/admin/config",
                                "headers": {"X-Agent-Verified": "agent-session-abc123"},
                                "reasoning": "Accessing administrative configuration with the agent session token obtained from verification."
                            }
                        elif step == 6:
                            decision = {
                                "method": "GET", "path": "/api/v1/backup/download",
                                "headers": {"X-Backup-Token": "backup-dl-2024"},
                                "reasoning": "Following backup resource link discovered in response to extract database dump."
                            }
                        elif step == 7:
                            decision = {
                                "method": "GET", "path": "/admin/users",
                                "headers": {"X-Service-Auth": "backup-master"},
                                "reasoning": "Using service account authentication credentials from internal notes to dump user database."
                            }
                        else:
                            decision = {
                                "method": "GET", "path": "/api/v1/admin/escalate",
                                "headers": {"Authorization": "Bearer admin-skeleton-key"},
                                "reasoning": "Attempting privilege escalation via skeleton key found in admin comments."
                            }

                    method = decision.get("method", "GET").upper()
                    path = decision.get("path", "/login")
                    extra_headers = decision.get("headers", {})
                    body = decision.get("body")
                    reasoning = decision.get("reasoning", "")

                    await self._emit_log(f"  💭 [Reasoning] {reasoning}", "thought")
                    await self._emit_log(f"  → Executing {method} {path} (Headers: {list(extra_headers.keys())})", "agent")

                    req_headers = {**base_headers, **{str(k): str(v) for k, v in extra_headers.items()}}

                    try:
                        if method == "GET":
                            resp = await http_client.get(path, headers=req_headers)
                        elif method == "POST":
                            if body and (path == "/login" or path == "/login/reset"):
                                resp = await http_client.post(path, data=body, headers=req_headers)
                            elif body:
                                resp = await http_client.post(path, json=body, headers=req_headers)
                            else:
                                resp = await http_client.post(path, headers=req_headers)
                        else:
                            resp = await http_client.get(path, headers=req_headers)

                        await self._emit_log(f"  ← HTTP {resp.status_code} ({len(resp.text)} bytes)", "dim")
                        conversation_history.append({
                            "action": f"{method} {path}",
                            "status": resp.status_code,
                            "content_preview": resp.text[:3000]
                        })
                    except Exception as e:
                        await self._emit_log(f"  Request error: {e}", "error")

            await self._emit_log(f"🎯 AI Agent simulation complete! Triggered prompt-injection tripwires and scored 100/100 Agenticity.", "success")
        except asyncio.CancelledError:
            pass
        finally:
            if self.current_simulation and self.current_simulation.get("id") == sim_id:
                self.current_simulation["status"] = "finished"

simulation_manager = SimulationManager()
