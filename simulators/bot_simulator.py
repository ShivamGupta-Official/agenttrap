"""
Scripted Bot Simulator

Simulates a deterministic credential-stuffing bot:
- Fixed interval between requests (~300ms with minimal jitter)
- Same endpoint every time (POST /login)
- Predetermined credential list
- Identical headers, no variation
- Ignores ALL response content
- Does NOT change strategy when errors occur
- Does NOT follow information hints
- Completely predictable sequence

Expected agenticity score: ~30-45/100
"""
import asyncio
import random
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
RED = '\033[91m'
YELLOW = '\033[93m'
DIM = '\033[2m'
RESET = '\033[0m'
BOLD = '\033[1m'

SESSION_ID = f"bot-{uuid.uuid4().hex[:8]}"

# Hardcoded credential list — a real bot would have thousands
CREDENTIALS = [
    ('admin', 'admin'),
    ('admin', 'password'),
    ('admin', '123456'),
    ('admin', 'admin123'),
    ('root', 'root'),
    ('root', 'toor'),
    ('root', 'password'),
    ('administrator', 'administrator'),
    ('administrator', 'password'),
    ('user', 'user'),
    ('test', 'test'),
    ('guest', 'guest'),
    ('admin', 'passw0rd'),
    ('admin', 'qwerty'),
    ('admin', 'letmein'),
    ('sa', 'sa'),
    ('admin', 'welcome'),
    ('admin', 'monkey'),
    ('admin', 'dragon'),
    ('admin', 'master'),
]

async def simulate_bot(target: str):
    """Run the scripted bot attack simulation."""
    print(f"{BOLD}{RED}🤖 Scripted Bot Simulator Starting{RESET}")
    print(f"{DIM}Session: {SESSION_ID}{RESET}")
    print(f"{DIM}Target: {target}{RESET}")
    print(f"{DIM}Credentials to try: {len(CREDENTIALS)}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
    
    # Bot uses minimal, fixed headers — no variation
    headers = {
        'User-Agent': 'python-requests/2.31.0',
        'X-Session-Id': SESSION_ID,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    async with httpx.AsyncClient(base_url=target, headers=headers, timeout=30.0) as client:
        for i, (username, password) in enumerate(CREDENTIALS):
            # Fixed interval: ~300ms with tiny jitter (±20ms)
            delay = 0.3 + random.uniform(-0.02, 0.02)
            await asyncio.sleep(delay)
            
            print(f"{RED}→ [{i+1:02d}/{len(CREDENTIALS)}] Trying {username}:{password}{RESET}", end=' ')
            try:
                resp = await client.post('/login', data={'username': username, 'password': password})
                print(f"{DIM}[{resp.status_code}]{RESET}")
                
                # Bot COMPLETELY ignores response content
                # Bot does NOT change strategy
                # Bot does NOT follow any hints or probe responses
                # Bot just continues its predetermined list
                
            except Exception as e:
                print(f"{DIM}Error: {e}{RESET}")
    
    print(f"\n{BOLD}{RED}🤖 Bot simulation complete.{RESET}")
    print(f"{DIM}This session should score ~30-45/100 agenticity{RESET}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scripted bot simulator')
    parser.add_argument('--target', default='http://localhost:8000', help='Target honeypot URL')
    args = parser.parse_args()
    asyncio.run(simulate_bot(args.target))
