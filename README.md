# 🍯 Are You Even Human?

**An AI-Attacker-Detecting Honeypot**

Traditional honeypots catch human hackers. This one is built specifically to catch **AI agents** attacking your systems — using the fact that LLM-based attackers think and act differently from humans, and that difference is exploitable.

## Architecture

```
Attacker (Human / Bot / AI Agent)
         │
         ▼
┌─────────────────────┐
│  DECOY HONEYPOT     │  Fake Login, Admin Panel, REST API
│  (FastAPI)          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  BEHAVIOURAL PROBES │  Error, Information, Environment Change, Path Block
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  BEHAVIOUR ENGINE   │  Adaptation, Context Usage, Error Recovery,
│                     │  Goal Persistence, Automation Pattern
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  AGENTICITY ENGINE  │  Score (0-100) + Evidence + Classification
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  SOC DASHBOARD      │  Real-time React dashboard with WebSocket
│  (React + Vite)     │
└─────────────────────┘
```

## 🚀 Instant Single-Link Deployment (GitHub Pages)

The entire project now features a **unified master showcase** in [`index.html`](file:///c:/Users/Shivam%20Gupta/.gemini/antigravity-ide/scratch/are-you-even-human/index.html) that combines:
- **Hero & Cyber Showcase** with glowing particle matrix
- **Live SOC Operations Console** with deep forensic dossiers & 5-signal behavioural radar
- **Interactive Attack Simulator Lab** with live streaming stdout terminal
- **Decoy Honeypot Sandbox** with hidden prompt-injection canary traps
- **Judge Architecture & Master Pitch** with scoring formulas and threat matrix

### Deploy to GitHub Pages in 1 Click:
1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: unified master landing page"
   git remote add origin https://github.com/<your-username>/are-you-even-human.git
   git branch -M main
   git push -u origin main
   ```
2. Go to **Settings > Pages** on your GitHub repository.
3. Under **Branch**, select `main` and `/ (root)`, then click **Save**.
4. **Done!** Your single URL will be live at:
   `https://<your-username>.github.io/are-you-even-human/`

---

## 💻 Local Quick Start

### 1. Start the Backend (Honeypot)
```bash
cd backend
pip install -r requirements.txt
python main.py
# → Master Showcase & Honeypot running at http://localhost:8000
```

### 2. Start the Dashboard
```bash
cd dashboard
npm install
npm run dev
# → Dashboard at http://localhost:3000
```

### 3. Run Attacker Simulators
```bash
cd simulators
pip install -r requirements.txt

# Terminal 1: Human-like attacker (score ~15-25)
python human_simulator.py

# Terminal 2: Scripted bot (score ~30-45)
python bot_simulator.py

# Terminal 3: AI Agent (score ~70-90) — requires Gemini API key
set GEMINI_API_KEY=your-key-here
python ai_agent_simulator.py
```

## Detection Signals

### 🧠 Five Behavioural Features

| Feature | What it measures | Human | Bot | AI Agent |
|---------|-----------------|-------|-----|----------|
| **Adaptation** | Strategy change after new info | Low | None | High |
| **Context Usage** | Uses info from responses | Low | None | High |
| **Error Recovery** | Changes approach after failures | Retries | Ignores | Adapts |
| **Goal Persistence** | Pursues objectives via different routes | Random | Fixed | Persistent |
| **Automation Pattern** | Predictability of interactions | Irregular | Metronomic | Moderate |

### 🎣 Behavioural Probes
The honeypot actively creates controlled situations:
- **Error Probe**: Returns unexpected errors → does the attacker adapt?
- **Information Probe**: Hints at new resources → does the attacker follow?
- **Environment Change**: Same request, different response → does it adjust?
- **Path Block**: Working path stops → does it find alternatives?

### 🎯 Tripwires
Hidden instructions (HTML comments, hidden divs, JS config) that only an LLM reading the full page content would follow.

## Tech Stack
- **Backend**: Python + FastAPI + SQLite
- **Dashboard**: React 19 + Vite + Recharts
- **AI Agent**: Google Gemini 2.0 Flash
