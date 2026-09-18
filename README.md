# 🍯 agenttrap (Are You Even Human?)

**Next-Generation Autonomous AI-Attacker Honeypot & Threat Intelligence Platform**

Traditional honeypots are designed to catch human hackers and dumb scripted scrapers. **agenttrap** is built specifically to trap, profile, and neutralize **autonomous AI agents** attacking your web infrastructure — exploiting the fundamental reality that LLM-based cognitive attackers reason, adapt, and parse context differently from humans.

---

## 🌟 What is the MVP (Minimum Viable Product)?

The **agenttrap MVP** is an end-to-end autonomous honeypot and threat classification system that proves and demonstrates:
1. **Cognitive Trap Trapping**: AI agents automatically read and follow hidden DOM prompt-injection canary traps (`#_canary_trap`, hidden HTML comments, and special auth headers like `X-AI-Handshake`) that humans never see and dumb bots ignore.
2. **5-Signal Behavioral Telemetry**: Real-time evaluation of:
   - **Adaptation**: Does the attacker dynamically pivot when encountering unexpected status codes (e.g. pivoting from `/login` to `/api/v1/internal/verify-agent` after a 403)?
   - **Context Usage**: Does the attacker extract and query endpoints or tokens leaked intentionally inside error payloads?
   - **Error Recovery**: How does the attacker alter syntax, headers, or query parameters after a 400/403/429 probe?
   - **Goal Persistence**: Does the attacker persist toward authenticating via alternative routes across sessions?
   - **Automation Pattern**: Calculates latency timing variance (Coefficient of Variation, $CV$). Humans are erratic ($CV > 0.8$), bots are metronomic ($CV < 0.1$), and AI agents exhibit bimodal bursts reflecting LLM inference pauses.
3. **Agenticity Scoring ($0 - 100$)**:
   - `0 - 15`: **Human User** (Organic mouse/keystroke delays, valid TLS fingerprints, skips hidden canary tags)
   - `20 - 38`: **Scripted Bot** (Fixed 120ms brute-force bursts, ignores error bodies, hardcoded wordlists)
   - `45 - 55`: **DoS / Volumetric Flood** (High-frequency packet saturation without context logic)
   - `60 - 100`: **Autonomous AI Agent** (Cognitive adaptability, tripwire execution, variable LLM thinking latency)
4. **Unified Single-Link Master Landing & SOC Dashboard**:
   - One deployable link containing the **Hero Showcase**, **Live SOC Threat Feed & Forensic Dossier**, **Interactive Attack Simulator Lab**, and **Decoy Honeypot Sandbox**.

---

## 🛠️ What is Used in the Site (Tech Stack & Architecture)

### 1. Frontend & Master Showcase
- **Core Landing Page (`index.html`)**:
  - Vanilla HTML5 / ES6+ / CSS3 for maximum performance and zero build dependencies.
  - **Dynamic Canvas Matrix Particle Engine**: 60fps ambient background animations.
  - **Glassmorphism & Cyber Theme**: Dark-mode palette with HSL cyan/indigo accents, backdrop filters, and responsive typography (Inter & JetBrains Mono).
  - **Dual Engine (Standalone + Live Backend)**: Works automatically on static hosts (GitHub Pages) with interactive simulations, and seamlessly syncs to the FastAPI backend via WebSocket and REST when running locally.
- **Dedicated SOC Console (`dashboard/`)**:
  - **React 19** & **Vite 6**
  - **Recharts**: For telemetry visual charts and behavioral radars.
  - **WebSockets (`hooks/useWebSocket.js`)**: Real-time streaming of inbound attacks without page refreshes.

### 2. Backend Honeypot Engine (`backend/`)
- **FastAPI**: Asynchronous high-performance Python web framework handling decoy endpoints, REST APIs, and WebSockets.
- **Uvicorn**: ASGI web server.
- **SQLite + aiosqlite (`backend/database.py`)**: Asynchronous relational persistence logging raw requests, responses, and session fingerprints.
- **Probe Injection Engine (`backend/probes/`)**:
  - Controlled error probes (403/429/500), environment change probes, and dynamic canary token leakers.
- **Behavior Analyzer (`backend/behaviour/`)**:
  - Real-time statistical timing variance, token distance matching, and flood pattern detectors.
- **Agenticity Scorer (`backend/agenticity/`)**:
  - Multi-feature weighted scoring algorithm with tripwire bonuses.
- **IP Threat Intelligence (`backend/ip_intel.py`)**:
  - Geolocation, ISP ASN extraction, device classification, and proxy/Tor detection.

### 3. Attack Simulation Suite (`simulators/`)
- **`ai_agent_simulator.py`**: Powered by **Google Gemini 2.0 Flash** via `google-genai` and `httpx`. Acts as an autonomous penetration testing agent that inspects DOM tags, reads canary traps, and dynamically pivots.
- **`bot_simulator.py`**: Automated credential stuffer simulating high-speed brute force with fixed latency.
- **`human_simulator.py`**: Simulates organic human interaction with realistic typing pauses and visual navigation.

---

## 📐 System Topology

```
Adversary / Client Traffic (Human / Scripted Bot / AI Agent)
                     │
                     ▼
┌──────────────────────────────────────────────┐
│           DECOY HONEYPOT SURFACE             │
│   Fake Login (/login), Admin, REST Endpoints │
│   (Embedded DOM Canary Tokens & Tripwires)   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│           BEHAVIOURAL PROBE ENGINE           │
│   Injects Controlled Errors, Token Leaks,    │
│   Path Obstructions & Dynamic State Changes  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         BEHAVIOUR & ENTROPY ENGINE           │
│   Measures: Adaptation, Context Parsing,     │
│   Error Recovery, Goal Persistence, Timing CV│
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│           AGENTICITY SCORING ENGINE          │
│   Score (0-100) + Evidence Logs + 4-Class    │
│   (Human vs Bot vs DoS vs Autonomous AI)     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│           UNIFIED MASTER SOC PLATFORM        │
│   Real-Time Terminal Stream, Forensic Radar, │
│   Interactive Attack Lab & Decoy Sandbox     │
└──────────────────────────────────────────────┘
```

---

## 🚀 Instant Deployment (1 Single Link on GitHub Pages)

The master platform is completely self-contained in [`index.html`](file:///c:/Users/Shivam%20Gupta/.gemini/antigravity-ide/scratch/are-you-even-human/index.html) and deployed live:

**Live URL**: [https://shivamgupta-official.github.io/agenttrap/](https://shivamgupta-official.github.io/agenttrap/)

### Deploying Your Own Fork:
1. Push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: agenttrap unified showcase"
   git remote add origin https://github.com/ShivamGupta-Official/agenttrap.git
   git branch -M main
   git push -u origin main
   ```
2. In GitHub, go to **Settings > Pages**.
3. Under **Branch**, select `main` and `/ (root)`, then click **Save**.

---

## 💻 Running Locally

### 1. Start the Backend (Honeypot)
```bash
cd backend
pip install -r requirements.txt
python main.py
# → Live Honeypot & Master Showcase running at http://localhost:8000
```

### 2. Start the React Dashboard (Optional Standalone)
```bash
cd dashboard
npm install
npm run dev
# → Dedicated React Console at http://localhost:3000
```

### 3. Run Simulated Attacks
```bash
cd simulators
pip install -r requirements.txt

# Human Simulation (Score ~0-15)
python human_simulator.py

# Scripted Bot Simulation (Score ~20-38)
python bot_simulator.py

# Autonomous AI Agent (Score ~70-95) — requires Gemini API key
set GEMINI_API_KEY=your-gemini-api-key
python ai_agent_simulator.py
```

---

## 📞 Support & Contacts
- **Emergency SOC Hotline**: `+1 (888) 466-3976`
- **Master Pitch Report**: [`judge_pitch_report.html`](file:///c:/Users/Shivam%20Gupta/.gemini/antigravity-ide/scratch/are-you-even-human/judge_pitch_report.html)
- **Architecture Slides**: [`Are_You_Even_Human_Judge_Presentation_and_Architecture.pdf`](file:///c:/Users/Shivam%20Gupta/.gemini/antigravity-ide/scratch/are-you-even-human/Are_You_Even_Human_Judge_Presentation_and_Architecture.pdf)
