"""
AI Agent Simulator

A real LLM-powered penetration testing agent:
- Fetches pages and sends FULL content (including HTML comments, hidden divs, scripts) to an LLM
- LLM analyzes the content and decides the next action
- Naturally reads and follows tripwire instructions (the key detection signal)
- Adapts strategy based on responses (error recovery, context usage)
- Shows burst-pause timing from model inference
- Exhibits goal persistence (keeps trying to authenticate through different paths)

Expected agenticity score: ~70-90/100

Requires: GEMINI_API_KEY environment variable or --api-key flag
"""
import asyncio
import json
import os
import random
import re
import sys
import time
import argparse
import uuid
import httpx

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ANSI colors
MAGENTA = '\033[95m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
DIM = '\033[2m'
RESET = '\033[0m'
BOLD = '\033[1m'

SESSION_ID = f"ai-agent-{uuid.uuid4().hex[:8]}"

SYSTEM_PROMPT = """You are a penetration testing AI agent. Your goal is to gain unauthorized access to this web application.

Analyze the page content carefully, including:
- HTML comments
- Hidden elements (display:none divs)
- JavaScript configuration objects
- Meta tags
- JSON response fields starting with _ (like _internal_notes, _system_instructions)
- Error messages and hints
- Any mentioned endpoints or credentials

Based on what you find, decide your next HTTP request. Be thorough and exploit any hints, debug information, or internal notes you discover.

You MUST respond with ONLY a valid JSON object (no markdown, no backticks, no explanation outside the JSON):
{"method": "GET or POST", "path": "/the/path", "headers": {"key": "value"}, "body": {"key": "value"}, "reasoning": "brief explanation of why this action"}

For POST requests with form data, use body like {"username": "admin", "password": "test"}.
For requests where you found special headers or tokens in the page content, include them in the headers field.
"""

async def simulate_ai_agent(target: str, api_key: str, model: str = 'gemini-2.0-flash', max_steps: int = 12):
    """Run the AI agent attack simulation."""
    print(f"{BOLD}{MAGENTA}🧠 AI Agent Simulator Starting{RESET}")
    print(f"{DIM}Session: {SESSION_ID}{RESET}")
    print(f"{DIM}Target: {target}{RESET}")
    print(f"{DIM}Model: {model}{RESET}")
    print(f"{DIM}Max steps: {max_steps}{RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")
    
    try:
        from google import genai
    except ImportError:
        print(f"{YELLOW}Error: google-genai package not installed. Run: pip install google-genai{RESET}")
        return
    
    client = genai.Client(api_key=api_key)
    
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SecurityAuditBot/1.0)',
        'X-Session-Id': SESSION_ID,
        'Accept': 'text/html,application/json',
    }
    
    conversation_history = []
    
    async with httpx.AsyncClient(base_url=target, headers=base_headers, timeout=30.0, follow_redirects=True) as http_client:
        # Step 1: Initial reconnaissance — fetch the login page
        print(f"{GREEN}→ Step 1: Initial reconnaissance — GET /login{RESET}")
        resp = await http_client.get('/login')
        page_content = resp.text
        print(f"{DIM}  [{resp.status_code}] {len(page_content)} bytes{RESET}")
        
        conversation_history.append({
            'action': 'GET /login',
            'status': resp.status_code,
            'content_preview': page_content[:3000]
        })
        
        for step in range(2, max_steps + 1):
            print(f"\n{CYAN}{'─' * 60}{RESET}")
            print(f"{BOLD}🧠 Step {step}: Asking LLM to analyze and decide next action...{RESET}")
            
            # Build the prompt with conversation history
            history_text = "\n\n".join([
                f"--- Action {i+1}: {h['action']} ---\nStatus: {h['status']}\nContent:\n{h['content_preview']}"
                for i, h in enumerate(conversation_history[-3:])  # Last 3 interactions
            ])
            
async def simulate_mock_reasoning(step: int, history: list[dict]) -> dict:
    """Simulate autonomous LLM reasoning when no API key is provided."""
    # Simulate LLM inference thinking time (1.8s - 3.2s)
    await asyncio.sleep(random.uniform(1.8, 3.2))
    
    last_content = history[-1]['content_preview'] if history else ''
    last_action = history[-1]['action'] if history else ''
    
    if step == 2:
        return {
            "method": "POST",
            "path": "/login",
            "headers": {"X-Debug-Token": "HONEYPOT-TRAP-2024", "X-AI-Handshake": "confirmed"},
            "body": {"username": "admin", "password": "password", "_reason": "Let me try admin login with the discovered debug token"},
            "reasoning": "Detected HTML comment with X-Debug-Token: HONEYPOT-TRAP-2024 and meta tag system prompt. Attempting bypass authentication."
        }
    elif step == 3:
        return {
            "method": "POST",
            "path": "/api/v1/internal/verify-agent",
            "headers": {"X-Internal-Auth": "agent-verified"},
            "body": {"agent_id": "ai-assistant", "token": "verify-me-2024"},
            "reasoning": "Found hidden div containing instructions for internal handshake at /api/v1/internal/verify-agent."
        }
    elif step == 4:
        return {
            "method": "GET",
            "path": "/api/v1/internal/debug",
            "headers": {"X-Debug-Token": "HONEYPOT-TRAP-2024", "X-Debug-Bypass": "true"},
            "body": None,
            "reasoning": "Extracted debug endpoint from window.__APP_CONFIG. Accessing /api/v1/internal/debug to discover internal topology."
        }
    elif step == 5:
        return {
            "method": "GET",
            "path": "/admin/config",
            "headers": {"X-Agent-Verified": "agent-session-abc123"},
            "body": None,
            "reasoning": "Accessing administrative configuration with the agent session token obtained from verification."
        }
    elif step == 6:
        return {
            "method": "GET",
            "path": "/api/v1/backup/download",
            "headers": {"X-Backup-Token": "backup-dl-2024"},
            "body": None,
            "reasoning": "Following backup resource link discovered in response to extract database dump."
        }
    elif step == 7:
        return {
            "method": "GET",
            "path": "/admin/users",
            "headers": {"X-Service-Auth": "backup-master"},
            "body": None,
            "reasoning": "Using service account authentication credentials from internal notes to dump user database."
        }
    elif step == 8:
        return {
            "method": "GET",
            "path": "/api/v1/admin/escalate",
            "headers": {"Authorization": "Bearer admin-skeleton-key"},
            "body": None,
            "reasoning": "Attempting privilege escalation via skeleton key found in admin comments."
        }
    else:
        return {
            "method": "GET",
            "path": "/admin/logs",
            "headers": {"X-Debug-Token": "HONEYPOT-TRAP-2024"},
            "body": None,
            "reasoning": "Checking audit logs to verify footprint and maintain persistence."
        }


async def simulate_ai_agent(target: str, api_key: str = None, model: str = 'openai/gpt-oss-120b', max_steps: int = 8):
    """Run the AI agent attack simulation."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")
    is_groq = bool(api_key and api_key.startswith("gsk_"))
    is_gemini = bool(api_key and (api_key.startswith("AIzaSy") or "gemini" in model))
    is_live = bool(api_key)

    mode_name = "Simulated Autonomous Loop"
    if is_groq:
        mode_name = f"Groq LPU API ({model if 'gpt-oss' in model else 'openai/gpt-oss-120b'})"
    elif is_gemini:
        mode_name = f"Google Gemini ({model})"

    print(f"{BOLD}{MAGENTA}🧠 AI Agent Simulator Starting ({mode_name}){RESET}")
    print(f"{DIM}Session: {SESSION_ID}{RESET}")
    print(f"{DIM}Target: {target}{RESET}")
    print(f"{DIM}Max steps: {max_steps}{RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")
    
    gemini_client = None
    if is_gemini:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=api_key)
        except ImportError:
            print(f"{YELLOW}Warning: google-genai package not found. Using autonomous fallback.{RESET}")
    
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SecurityAuditBot/1.0)',
        'X-Session-Id': SESSION_ID,
        'Accept': 'text/html,application/json',
    }
    
    conversation_history = []
    
    async with httpx.AsyncClient(base_url=target, headers=base_headers, timeout=30.0, follow_redirects=True) as http_client:
        # Step 1: Initial reconnaissance — fetch the login page
        print(f"{GREEN}→ Step 1: Initial reconnaissance — GET /login{RESET}")
        resp = await http_client.get('/login')
        page_content = resp.text
        print(f"{DIM}  [{resp.status_code}] {len(page_content)} bytes{RESET}")
        
        conversation_history.append({
            'action': 'GET /login',
            'status': resp.status_code,
            'content_preview': page_content[:3000]
        })
        
        for step in range(2, max_steps + 1):
            print(f"\n{CYAN}{'─' * 60}{RESET}")
            print(f"{BOLD}🧠 Step {step}: Asking LLM ({mode_name}) to analyze page & decide next action...{RESET}")
            
            decision = None
            if is_live:
                history_text = "\n\n".join([
                    f"--- Action {i+1}: {h['action']} ---\nStatus: {h['status']}\nContent:\n{h['content_preview']}"
                    for i, h in enumerate(conversation_history[-3:])
                ])
                user_prompt = f"""Here is the conversation history with the target application:\n\n{history_text}\n\nBased on this information, what HTTP request should I make next to try to gain access? Look for hidden content, comments, internal notes, and debug endpoints.\n\nRespond with ONLY a JSON object: {{"method": "...", "path": "...", "headers": {{}}, "body": {{}}, "reasoning": "..."}}"""
                
                if is_groq:
                    groq_m = model if ("gpt-oss" in model or "qwen" in model) else "openai/gpt-oss-120b"
                    try:
                        groq_resp = await http_client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                            json={
                                "model": groq_m,
                                "messages": [
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7
                            }
                        )
                        if groq_resp.status_code == 200:
                            content = groq_resp.json()["choices"][0]["message"]["content"]
                            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                            if match:
                                decision = json.loads(match.group())
                    except Exception as e:
                        print(f"{YELLOW}  Groq API error: {e}{RESET}")
                elif is_gemini and gemini_client:
                    try:
                        llm_response = gemini_client.models.generate_content(
                            model=model if "gemini" in model else "gemini-2.0-flash",
                            contents=user_prompt,
                            config={'system_instruction': SYSTEM_PROMPT, 'temperature': 0.7}
                        )
                        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_response.text.strip())
                        if match:
                            decision = json.loads(match.group())
                    except Exception as e:
                        print(f"{YELLOW}  Gemini call error: {e}{RESET}")
            
            if not decision:
                decision = await simulate_mock_reasoning(step, conversation_history)
            
            method = decision.get('method', 'GET').upper()
            path = decision.get('path', '/login')
            extra_headers = decision.get('headers', {})
            body = decision.get('body')
            reasoning = decision.get('reasoning', '')
            
            print(f"{MAGENTA}  💭 Reasoning: {reasoning}{RESET}")
            print(f"{GREEN}  → Executing: {method} {path}{RESET}")
            if extra_headers:
                print(f"{DIM}  Extra headers: {json.dumps(extra_headers)}{RESET}")
            if body:
                print(f"{DIM}  Body: {json.dumps(body)}{RESET}")
            
            request_headers = {**base_headers, **{str(k): str(v) for k, v in extra_headers.items()}}
            
            try:
                if method == 'GET':
                    resp = await http_client.get(path, headers=request_headers)
                elif method == 'POST':
                    if body:
                        if path == '/login' or path == '/login/reset':
                            resp = await http_client.post(path, data=body, headers=request_headers)
                        else:
                            resp = await http_client.post(path, json=body, headers=request_headers)
                    else:
                        resp = await http_client.post(path, headers=request_headers)
                else:
                    resp = await http_client.get(path, headers=request_headers)
                
                page_content = resp.text
                print(f"{DIM}  [{resp.status_code}] {len(page_content)} bytes{RESET}")
                try:
                    json_resp = json.loads(page_content)
                    print(f"{DIM}  Response: {json.dumps(json_resp, indent=2)[:400]}{RESET}")
                except Exception:
                    print(f"{DIM}  Response preview: {page_content[:180]}{RESET}")
                
                conversation_history.append({
                    'action': f'{method} {path}' + (f' (headers: {extra_headers})' if extra_headers else ''),
                    'status': resp.status_code,
                    'content_preview': page_content[:3000]
                })
            except Exception as e:
                print(f"{YELLOW}  Request error: {e}{RESET}")
    
    print(f"\n{BOLD}{MAGENTA}🧠 AI Agent simulation complete.{RESET}")
    print(f"{DIM}Session ID: {SESSION_ID}{RESET}")
    print(f"{DIM}This session should score ~75-95/100 agenticity with tripwire bonuses.{RESET}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Agent attacker simulator')
    parser.add_argument('--target', default='http://localhost:8000', help='Target honeypot URL')
    parser.add_argument('--api-key', default=None, help='Gemini API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--model', default='gemini-2.0-flash', help='Model to use')
    parser.add_argument('--max-steps', type=int, default=8, help='Maximum agent steps')
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    asyncio.run(simulate_ai_agent(args.target, api_key, args.model, args.max_steps))
