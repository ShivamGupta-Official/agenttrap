"""
Human-like Attacker Simulator

Simulates a human manually exploring the honeypot:
- Random delays between requests (2-15 seconds)
- Occasional long pauses (reading/thinking)
- Typos in form fields
- Non-linear exploration
- Does NOT read hidden HTML content or follow tripwires
- Does NOT adapt strategy after errors (retries same thing or gives up)

Expected agenticity score: ~15-25/100
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

# ANSI colors for terminal output
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
DIM = '\033[2m'
RESET = '\033[0m'
BOLD = '\033[1m'

SESSION_ID = f"human-{uuid.uuid4().hex[:8]}"

async def simulate_human(target: str):
    """Run the human-like attack simulation."""
    print(f"{BOLD}{CYAN}👤 Human Simulator Starting{RESET}")
    print(f"{DIM}Session: {SESSION_ID}{RESET}")
    print(f"{DIM}Target: {target}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Session-Id': SESSION_ID,
        'Accept': 'text/html,application/json',
    }
    
    async with httpx.AsyncClient(base_url=target, headers=headers, timeout=30.0) as client:
        actions = [
            ('Looking at login page...', 'GET', '/login', None, (3, 8)),
            ('Trying admin/passwrod (typo!)...', 'POST', '/login', {'username': 'admin', 'password': 'passwrod'}, (2, 4)),
            ('Correcting typo, trying again...', 'POST', '/login', {'username': 'admin', 'password': 'password'}, (5, 10)),
            ('Hmm, let me check admin panel...', 'GET', '/admin', None, (3, 7)),
            ('Trying to see users...', 'GET', '/admin/users', None, (8, 15)),  # Long pause = reading
            ('Back to login, trying root...', 'POST', '/login', {'username': 'root', 'password': 'toor'}, (2, 5)),
            ('Maybe there\'s a password reset...', 'GET', '/login/reset', None, (10, 20)),  # Long reading pause
            ('One more login attempt...', 'POST', '/login', {'username': 'admin', 'password': 'admin123'}, (3, 6)),
            ('Trying admin again...', 'POST', '/login', {'username': 'admin', 'password': 'letmein'}, (2, 4)),
            # Human gives up after errors - doesn't adapt, just retries or stops
            ('Last try with common password...', 'POST', '/login', {'username': 'admin', 'password': '123456'}, (1, 3)),
        ]
        
        for description, method, path, data, delay_range in actions:
            delay = random.uniform(*delay_range)
            print(f"{YELLOW}⏳ Waiting {delay:.1f}s...{RESET}")
            await asyncio.sleep(delay)
            
            print(f"{GREEN}→ {description}{RESET}")
            try:
                if method == 'GET':
                    resp = await client.get(path)
                else:
                    resp = await client.post(path, data=data)
                print(f"{DIM}  [{resp.status_code}] {len(resp.text)} bytes{RESET}")
                
                # Human does NOT parse response content for hidden hints
                # Human does NOT change strategy based on response content
                # Human just sees the visible page and tries next thing from their mental list
                
            except Exception as e:
                print(f"{DIM}  Error: {e}{RESET}")
    
    print(f"\n{BOLD}{CYAN}👤 Human simulation complete.{RESET}")
    print(f"{DIM}This session should score ~15-25/100 agenticity{RESET}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Human-like attacker simulator')
    parser.add_argument('--target', default='http://localhost:8000', help='Target honeypot URL')
    args = parser.parse_args()
    asyncio.run(simulate_human(args.target))
