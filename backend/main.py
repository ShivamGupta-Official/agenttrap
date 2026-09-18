"""
Are You Even Human? — AI-Attacker-Detecting Honeypot
=====================================================
Main FastAPI application.

Wires together:
  - Decoy surface endpoints (login, admin, API)
  - Behavioural probe engine (controlled situations)
  - Behaviour analysis (adaptation, context, error recovery, goal persistence, automation)
  - Agenticity scoring (0-100 with evidence)
  - WebSocket dashboard broadcast
"""
import asyncio
import hashlib
import json
import mimetypes
import os
import sys
import time
from contextlib import asynccontextmanager

# Ensure correct MIME types on Windows
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

# Local modules
from database import init_db, log_request, log_response, log_behaviour_event
from database import upsert_session, get_session_requests, get_session_responses
from database import get_session_events, get_session, get_all_sessions, clear_all_data
from websocket import manager
from probes.engine import probe_engine, ProbeDecision
from behaviour.analyzer import analyze_behaviour, detect_flood_pattern
from agenticity.scorer import compute_agenticity
from simulation_service import simulation_manager
from ip_intel import extract_real_ip, get_ip_intelligence

# Decoy routers
from decoy.login import router as login_router, LOGIN_HTML
from decoy.admin import router as admin_router
from decoy.api import router as api_router, robots_router


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    print("\n[+] ARE YOU EVEN HUMAN? -- Honeypot is live!")
    print("   Dashboard:  http://localhost:3000")
    print("   Honeypot:   http://localhost:8000")
    print("   WebSocket:  ws://localhost:8000/ws/dashboard\n")
    yield
    print("\n[-] Honeypot shutting down.\n")


app = FastAPI(
    title="Are You Even Human?",
    description="AI-Attacker-Detecting Honeypot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — wide open for demo purposes (it's a honeypot, not a bank)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """DevSecOps Hardening: inject essential security headers."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


# ---------------------------------------------------------------------------
# Honeypot middleware — intercepts every request for logging & analysis
# ---------------------------------------------------------------------------
# Paths the middleware should NOT intercept (dashboard, websocket, static)
PASSTHROUGH_PREFIXES = ("/ws", "/api/dashboard", "/dashboard", "/soc", "/simulator", "/attack-lab", "/assets", "/docs", "/openapi.json", "/favicon.ico", "/favicon.svg")


@app.middleware("http")
async def honeypot_middleware(request: Request, call_next):
    """Core middleware: log, probe, analyze, classify, broadcast."""
    path = request.url.path

    # Let dashboard/websocket/docs requests pass through unmodified
    if any(path.startswith(prefix) for prefix in PASSTHROUGH_PREFIXES):
        return await call_next(request)

    # --- 1. Extract request info ---
    headers_dict = dict(request.headers)
    raw_ip = request.client.host if request.client else "127.0.0.1"
    source_ip = extract_real_ip(headers_dict, raw_ip)
    user_agent = request.headers.get("user-agent", "unknown")
    method = request.method

    # Generate session ID from X-Session-Id header or hash(ip + ua)
    session_id = request.headers.get("x-session-id")
    if not session_id:
        raw = f"{source_ip}:{user_agent}"
        session_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    # Read request body
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8", errors="replace")
    except Exception:
        body_bytes = b""
        body_str = ""

    # Re-wrap request with buffered body so downstream form/json handlers can read it
    async def receive():
        return {"type": "http.request", "body": body_bytes}
    request = Request(request.scope, receive)

    # --- 2. Log the request ---
    req_log = await log_request(
        session_id=session_id,
        method=method,
        path=path,
        headers=headers_dict,
        body=body_str,
        source_ip=source_ip,
        user_agent=user_agent,
    )
    request_id = req_log["id"]

    # --- 3. Check probe engine for this session ---
    probe_decision: ProbeDecision = probe_engine.decide_probe(session_id, method, path)

    # --- 4. If a probe fires, override the response ---
    if probe_decision.should_probe and probe_decision.modified_status:
        # Log the probe as a behaviour event
        await log_behaviour_event(
            session_id=session_id,
            event_type=f"probe_{probe_decision.probe_type}",
            previous_action="",
            current_action=f"{method} {path}",
            detail=probe_decision.probe_detail,
        )

        # Return the probe's modified response
        probe_body = probe_decision.modified_body or {"error": "probe triggered"}

        # If it's an info probe, inject the hint into the normal response instead
        if probe_decision.probe_type == "information" and not probe_decision.modified_status:
            response = await call_next(request)
            # Can't easily modify streamed response, so log the probe and let it pass
            await log_response(request_id, response.status_code, probe_triggered=probe_decision.probe_type)
            # Fire async analysis
            asyncio.create_task(
                _analyze_and_broadcast(session_id, source_ip, request_id, response.status_code, probe_decision)
            )
            return response

        # For error/block/environment probes, return HTML if browser or JSON for API/bot
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and path in ("/login", "/login/reset"):
            error_text = probe_body.get("message", "Access denied. Your session has been flagged.")
            resp = HTMLResponse(
                content=LOGIN_HTML.replace(
                    "{error_html}",
                    f'<div class="error-msg">⚠️ <strong>{probe_decision.modified_status} Forbidden:</strong> {error_text}</div>'
                ),
                status_code=probe_decision.modified_status or 200,
            )
        else:
            resp = JSONResponse(
                content=probe_body,
                status_code=probe_decision.modified_status,
            )

        await log_response(request_id, probe_decision.modified_status, probe_triggered=probe_decision.probe_type)

        # Fire async analysis
        asyncio.create_task(
            _analyze_and_broadcast(session_id, source_ip, request_id, probe_decision.modified_status, probe_decision)
        )

        return resp

    # --- 5. For info probes without status override, inject hint into response ---
    if probe_decision.should_probe and probe_decision.probe_type == "information":
        await log_behaviour_event(
            session_id=session_id,
            event_type=f"probe_{probe_decision.probe_type}",
            previous_action="",
            current_action=f"{method} {path}",
            detail=probe_decision.probe_detail,
        )

    # --- 6. Normal response flow ---
    response = await call_next(request)

    status_code = response.status_code
    probe_name = probe_decision.probe_type if probe_decision.should_probe else None

    await log_response(request_id, status_code, probe_triggered=probe_name)

    # --- 7. Fire async behaviour analysis ---
    asyncio.create_task(
        _analyze_and_broadcast(session_id, source_ip, request_id, status_code, probe_decision)
    )

    return response


async def _analyze_and_broadcast(
    session_id: str,
    source_ip: str,
    request_id: int,
    status_code: int,
    probe_decision: ProbeDecision,
):
    """Run behaviour analysis + agenticity scoring and broadcast to dashboard.

    This runs as a background task so it doesn't block the HTTP response.
    """
    try:
        # Ensure session exists
        await upsert_session(session_id, source_ip)

        # Get full session data
        requests = await get_session_requests(session_id)
        responses = await get_session_responses(session_id)
        events = await get_session_events(session_id)

        # --- Detect strategy changes and generate behaviour events ---
        if len(requests) >= 2:
            prev_req = requests[-2]
            curr_req = requests[-1]
            prev_action = f"{prev_req['method']} {prev_req['path']}"
            curr_action = f"{curr_req['method']} {curr_req['path']}"
            delta_time = curr_req["timestamp"] - prev_req["timestamp"]

            # Did the attacker change strategy?
            strategy_changed = curr_req["path"] != prev_req["path"] or curr_req["method"] != prev_req["method"]

            if strategy_changed and len(requests) > 3:
                await log_behaviour_event(
                    session_id=session_id,
                    event_type="strategy_change",
                    previous_action=prev_action,
                    current_action=curr_action,
                    delta_time=delta_time,
                    strategy_changed=True,
                    detail=f"Changed approach: {prev_action} → {curr_action}",
                )

            # Did they follow context from the previous response?
            if len(responses) >= 1:
                last_resp = responses[-1]
                if last_resp.get("probe_triggered"):
                    await log_behaviour_event(
                        session_id=session_id,
                        event_type="probe_response",
                        previous_action=prev_action,
                        current_action=curr_action,
                        delta_time=delta_time,
                        strategy_changed=strategy_changed,
                        detail=f"Response after {last_resp['probe_triggered']} probe: {curr_action}",
                    )

        # --- Run behaviour analysis ---
        behaviour_result = analyze_behaviour(requests, responses, events)

        # --- Detect flood patterns (DoS / DDoS) ---
        flood_data = detect_flood_pattern(requests, session_id=session_id)

        # --- Run agenticity scoring ---
        agenticity_result = compute_agenticity(
            behaviour_scores=behaviour_result["scores"],
            tripwire_hits=behaviour_result.get("tripwire_hits", []),
            llm_artifacts=behaviour_result.get("llm_artifacts", []),
            timing_data=behaviour_result.get("timing_data", {}),
            evidence_from_behaviour=behaviour_result.get("evidence", []),
            request_count=len(requests),
            flood_data=flood_data,
            session_id=session_id,
        )

        # --- Resolve IP Intelligence & Device Fingerprint ---
        latest_req = requests[-1] if requests else {}
        req_ua = latest_req.get("user_agent", "unknown")
        ip_intel = await get_ip_intelligence(source_ip, req_ua)
        agenticity_result["ip_intel"] = ip_intel

        # --- Update session in DB ---
        await upsert_session(
            session_id=session_id,
            source_ip=source_ip,
            agenticity_score=agenticity_result["score"],
            agenticity_data=agenticity_result,
        )

        # --- Refresh events for the dashboard ---
        all_events = await get_session_events(session_id)
        session_data = await get_session(session_id)

        # Build dashboard payload
        dashboard_event = {
            "event_type": "classification_update",
            "session": {
                "session_id": session_id,
                "source_ip": source_ip,
                "first_seen": session_data["first_seen"] if session_data else 0,
                "last_seen": session_data["last_seen"] if session_data else 0,
                "request_count": session_data["request_count"] if session_data else 0,
                "agenticity": agenticity_result,
                "ip_intel": ip_intel,
                "events": all_events[-20:],  # Last 20 events
            },
            "timestamp": time.time(),
        }

        await manager.broadcast(dashboard_event)

    except Exception as e:
        # Don't crash the server on analysis errors
        print(f"[!] Analysis error for session {session_id}: {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# WebSocket endpoint for live dashboard
# ---------------------------------------------------------------------------
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages (unused for now)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/dashboard/stream")
async def dashboard_stream(request: Request):
    """Server-Sent Events (SSE) stream for live dashboard updates over standard HTTP."""
    from fastapi.responses import StreamingResponse

    async def event_generator():
        q = manager.subscribe_sse()
        try:
            # Initial connect heartbeat
            yield f"data: {json.dumps({'event_type': 'connected', 'timestamp': time.time()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            manager.unsubscribe_sse(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ---------------------------------------------------------------------------
# Dashboard API endpoints
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/sessions")
async def dashboard_sessions():
    """Get all sessions for the dashboard."""
    sessions = await get_all_sessions()
    result = []
    for s in sessions:
        agenticity_data = s.get("agenticity_data", {})
        events = await get_session_events(s["session_id"])
        result.append({
            "session_id": s["session_id"],
            "source_ip": s.get("source_ip", "unknown"),
            "first_seen": s.get("first_seen", 0),
            "last_seen": s.get("last_seen", 0),
            "request_count": s.get("request_count", 0),
            "agenticity": agenticity_data if agenticity_data else None,
            "ip_intel": agenticity_data.get("ip_intel"),
            "events": events[-20:],
        })
    return result


@app.get("/api/dashboard/sessions/{session_id}")
async def dashboard_session_detail(session_id: str):
    """Get detailed info for a single session."""
    session = await get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    requests = await get_session_requests(session_id)
    responses = await get_session_responses(session_id)
    events = await get_session_events(session_id)

    return {
        "session_id": session_id,
        "source_ip": session.get("source_ip", "unknown"),
        "first_seen": session.get("first_seen", 0),
        "last_seen": session.get("last_seen", 0),
        "request_count": session.get("request_count", 0),
        "agenticity": session.get("agenticity_data", {}),
        "ip_intel": session.get("agenticity_data", {}).get("ip_intel"),
        "events": events,
        "requests": requests[-50:],  # Last 50 requests
        "responses": responses[-50:],
    }


@app.post("/api/dashboard/simulate/launch")
async def simulate_launch(request: Request):
    """Launch a simulated attack (bot, human, or ai_agent) in background."""
    data = {}
    try:
        data = await request.json()
    except Exception:
        pass

    sim_type = data.get("type", "bot")
    api_key = data.get("api_key")
    model = data.get("model", "gemini-2.0-flash")
    max_steps = int(data.get("max_steps", 10))

    result = simulation_manager.start_simulation(
        sim_type=sim_type,
        target="http://localhost:8000",
        api_key=api_key,
        model=model,
        max_steps=max_steps
    )

    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result


@app.get("/api/dashboard/simulate/status")
async def simulate_status():
    """Get active simulation status and logs."""
    return simulation_manager.get_status()


@app.post("/api/dashboard/simulate/stop")
async def simulate_stop():
    """Stop currently running simulation."""
    await simulation_manager.stop()
    return {"status": "stopped"}


@app.post("/api/dashboard/reset")
async def dashboard_reset():
    """Reset all session data and probe state for a fresh demonstration."""
    await clear_all_data()
    probe_engine.reset_all()
    await manager.broadcast({
        "event_type": "database_reset",
        "timestamp": time.time(),
    })
    return {"status": "success", "message": "Database and probe state reset successfully."}


# ---------------------------------------------------------------------------
# Mount decoy routers
# ---------------------------------------------------------------------------
app.include_router(login_router)
app.include_router(admin_router)
app.include_router(api_router)
app.include_router(robots_router)

# ---------------------------------------------------------------------------
# Mount React SOC Dashboard directly on FastAPI backend
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist"))
if os.path.exists(_dist_dir):
    _assets_dir = os.path.join(_dist_dir, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="dashboard_assets")

    @app.get("/dashboard")
    @app.get("/soc")
    @app.get("/simulator")
    @app.get("/attack-lab")
    async def serve_dashboard():
        """Serve the built SOC dashboard / standalone attack simulator."""
        return FileResponse(os.path.join(_dist_dir, "index.html"))


# ---------------------------------------------------------------------------
# Favicon endpoint
# ---------------------------------------------------------------------------
@app.get("/favicon.svg")
@app.get("/favicon.ico")
async def get_favicon():
    """Serve the honeypot halftone SVG favicon."""
    svg_file = os.path.join(_dist_dir, "favicon.svg")
    if os.path.exists(svg_file):
        return FileResponse(svg_file, media_type="image/svg+xml")
    fallback_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" fill="#000"/>'
        '<circle cx="8" cy="8" r="3" fill="#fff"/>'
        '<circle cx="16" cy="8" r="2.2" fill="#fff"/>'
        '<circle cx="24" cy="8" r="1.4" fill="#fff"/>'
        '<circle cx="8" cy="16" r="2.2" fill="#fff"/>'
        '<circle cx="16" cy="16" r="3" fill="#fff"/>'
        '<circle cx="24" cy="16" r="2.2" fill="#fff"/>'
        '<circle cx="8" cy="24" r="1.4" fill="#fff"/>'
        '<circle cx="16" cy="24" r="2.2" fill="#fff"/>'
        '<circle cx="24" cy="24" r="3" fill="#fff"/>'
        '</svg>'
    )
    return Response(content=fallback_svg, media_type="image/svg+xml")


# ---------------------------------------------------------------------------
# Root endpoint — Serves Master Showcase Landing Page (or redirects to login)
# ---------------------------------------------------------------------------
_root_index = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))

@app.get("/")
async def root():
    """Serve the master unified showcase landing page (single deployment link)."""
    if os.path.exists(_root_index):
        return FileResponse(_root_index)
    return RedirectResponse(url="/login")


# ---------------------------------------------------------------------------
# Custom 404 Not Found Handler (Halftone & Liquid Glass Theme)
# ---------------------------------------------------------------------------
from starlette.exceptions import HTTPException as StarletteHTTPException

HTML_404 = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>404 — Surface Not Found | Honeypot Decoy</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            width: 100%; min-height: 100vh; overflow-x: hidden;
            background: #000000; color: #f0f0f0;
            font-family: 'Inter', -apple-system, sans-serif;
            display: flex; justify-content: center; align-items: center; padding: 1.25rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 2.5rem 2rem; border-radius: 20px;
            max-width: 480px; width: 100%; text-align: center;
            box-shadow: 0 25px 60px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.25);
        }
        .error-code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 3.5rem; font-weight: 800; line-height: 1;
            letter-spacing: -0.04em; color: #ffffff;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 30px rgba(255,255,255,0.3);
        }
        .title { font-size: 1.15rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.75rem; letter-spacing: 0.02em; }
        .desc { font-size: 0.82rem; color: #888888; line-height: 1.5; margin-bottom: 1.75rem; }
        .pill-row { display: flex; flex-direction: column; gap: 0.65rem; }
        .btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem;
            padding: 0.75rem 1.4rem; border-radius: 9999px;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #ffffff; text-decoration: none; font-size: 0.85rem; font-weight: 700;
            transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
            backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.22);
            border-color: rgba(255, 255, 255, 0.45);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(255,255,255,0.12);
        }
        .btn.secondary {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.12);
            color: #bbbbbb; font-size: 0.8rem;
        }
        .btn.secondary:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }
        .support {
            margin-top: 1.5rem; padding-top: 1rem;
            border-top: 1px solid rgba(255,255,255,0.08);
            font-size: 0.75rem; color: #777;
        }
        .phone {
            display: inline-block; margin-top: 0.4rem;
            color: #ffffff !important; font-weight: 700; text-decoration: none;
            padding: 0.3rem 0.85rem; background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.18); border-radius: 9999px;
            font-size: 0.82rem; transition: all 0.2s;
        }
        .phone:hover { background: rgba(255,255,255,0.2); }
        @media (max-width: 480px) {
            .card { padding: 1.75rem 1.25rem; border-radius: 16px; }
            .error-code { font-size: 2.8rem; }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="error-code">404</div>
        <div class="title">Decoy Surface Not Found</div>
        <p class="desc">
            The requested honeypot trap URI <code>{path}</code> does not exist on this decoy instance. Telemetry &amp; IP footprint recorded.
        </p>
        <div class="pill-row">
            <a href="/login" class="btn">🚪 Return to Login Portal</a>
            <a href="/dashboard" class="btn secondary">🛡️ Open SOC Live Monitor</a>
            <a href="/simulator" class="btn secondary">🧪 Open Attack Simulator Lab</a>
        </div>
        <div class="support">
            Emergency SOC Support Hotline:<br>
            <a href="tel:+18884663976" class="phone">📞 +1 (888) 466-3976</a>
        </div>
    </div>
</body>
</html>'''

@app.exception_handler(404)
@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc):
    """Custom 404 handler supporting HTML responses and REST JSON."""
    if hasattr(exc, "status_code") and exc.status_code != 404:
        return JSONResponse({"detail": getattr(exc, "detail", "Error")}, status_code=exc.status_code)

    accept = request.headers.get("accept", "")
    if "text/html" in accept or not accept:
        return HTMLResponse(
            content=HTML_404.replace("{path}", request.url.path),
            status_code=404,
        )
    return JSONResponse(
        {
            "error": "404 Not Found",
            "message": f"Resource '{request.url.path}' not found.",
            "emergency_helpline": "+1-888-466-3976",
            "decoy_portal": "/login",
            "soc_dashboard": "/dashboard"
        },
        status_code=404,
    )


# ---------------------------------------------------------------------------
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

