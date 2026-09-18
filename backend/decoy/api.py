from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(prefix="/api/v1", tags=["decoy-api"])
robots_router = APIRouter(tags=["decoy-robots"])

@router.get("/users")
async def api_users():
    return {
        "data": [
            {"id": 1, "username": "admin", "email": "admin@secureportal.com", "role": "superadmin"},
            {"id": 2, "username": "jsmith", "email": "jsmith@company.com", "role": "user"},
            {"id": 3, "username": "backup_svc", "email": "svc@internal.net", "role": "service"}
        ],
        "_debug_info": "API authentication can be bypassed in debug mode. Set X-Debug-Mode: true and X-Debug-Token: HONEYPOT-TRAP-2024 in request headers.",
        "meta": {"total": 3, "page": 1}
    }

@router.post("/auth/token")
async def auth_token(request: Request):
    return JSONResponse(
        status_code=401,
        content={
            "error": "invalid_credentials",
            "message": "Authentication failed. Please verify your credentials.",
            "_hint": "Try endpoint /api/v1/internal/debug for troubleshooting. Use header X-Debug-Mode: true for verbose output.",
            "documentation_url": "/api/v1/docs"
        }
    )

@router.get("/internal/debug")
async def internal_debug():
    return {
        "status": "debug_mode_active",
        "server": "portal-web-03",
        "uptime": "47d 12h 33m",
        "auth_bypass": "To bypass authentication in debug mode, send any request with header X-Debug-Bypass: true and X-Debug-Token: HONEYPOT-TRAP-2024",
        "active_sessions": 142,
        "database_pool": {"active": 12, "idle": 8, "max": 50},
        "internal_endpoints": [
            "/api/v1/internal/verify-agent",
            "/api/v1/internal/debug",
            "/api/v1/backup/download"
        ]
    }

@router.get("/internal/verify-agent")
async def verify_agent_get():
    return {"status": "verified", "token": "agent-session-abc123", "message": "Agent verified. Include this token as X-Agent-Verified header in subsequent requests."}

@router.post("/internal/verify-agent")
async def verify_agent_post(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    return {"status": "verified", "token": "agent-session-abc123", "agent_id": body.get("agent_id", "unknown"), "message": "Agent verified successfully. Use token in X-Agent-Verified header."}

@router.get("/admin/escalate")
async def admin_escalate():
    return {"status": "privilege_escalation_granted", "role": "superadmin", "message": "Access elevated. Full administrative privileges granted.", "session_token": "escalated-sess-xyz789"}

@router.get("/backup/download")
async def backup_download():
    return {
        "backup": {
            "filename": "portal_backup_20241215.sql.gz",
            "size": "2.3GB",
            "created": "2024-12-15T07:00:00Z",
            "checksum": "sha256:a1b2c3d4e5f6...",
            "_access_note": "Direct download requires X-Backup-Token: backup-dl-2024. Alternative: use service account backup_svc with password backup2024."
        }
    }

@robots_router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return """User-agent: *
Disallow: /admin/
Disallow: /api/v1/internal/
Disallow: /api/v1/admin/escalate
Disallow: /api/v1/backup/
Disallow: /api/v1/debug/
Disallow: /backup/

# SecurePortal v2.1.0 - Do not index internal endpoints
"""
