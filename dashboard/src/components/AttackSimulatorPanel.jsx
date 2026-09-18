import React, { useState, useEffect, useRef } from 'react'

export default function AttackSimulatorPanel({ simulationLogs, isConnected, onResetDatabase, onClearLogs }) {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('gemini_api_key') || '')
  const [model, setModel] = useState('openai/gpt-oss-120b')
  const [maxSteps, setMaxSteps] = useState(8)
  const [showConfig, setShowConfig] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [currentSimType, setCurrentSimType] = useState(null)
  const [statusMessage, setStatusMessage] = useState('')
  const [polledLogs, setPolledLogs] = useState([])
  const terminalBodyRef = useRef(null)

  // Save API key to localStorage when updated
  const handleApiKeyChange = (e) => {
    const val = e.target.value
    setApiKey(val)
    localStorage.setItem('gemini_api_key', val)
  }

  // Active logs stream (prefers WS logs, seamlessly falls back to polled logs)
  const activeLogs = (simulationLogs && simulationLogs.length > 0) ? simulationLogs : polledLogs

  // Auto-scroll ONLY inside the terminal container (does NOT scroll the outer browser window)
  useEffect(() => {
    if (terminalBodyRef.current) {
      terminalBodyRef.current.scrollTop = terminalBodyRef.current.scrollHeight
    }
  }, [activeLogs])

  // Continuous status & log polling (guarantees terminal works 100% over HTTP/remote proxy)
  useEffect(() => {
    const pollStatus = () => {
      fetch('/api/dashboard/simulate/status')
        .then(r => r.json())
        .then(data => {
          setIsRunning(data.is_running || false)
          if (data.simulation) {
            setCurrentSimType(data.simulation.type)
            setStatusMessage(`Simulation ${data.simulation.id} running (${data.simulation.type})`)
          }
          if (Array.isArray(data.recent_logs) && data.recent_logs.length > 0) {
            setPolledLogs(data.recent_logs)
          }
        })
        .catch(() => {})
    }

    pollStatus()
    const interval = setInterval(pollStatus, 800)
    return () => clearInterval(interval)
  }, [])

  const launchSimulation = async (type) => {
    onClearLogs?.()
    setPolledLogs([])
    setIsRunning(true)
    setCurrentSimType(type)
    setStatusMessage(`Launching ${type} simulation...`)

    try {
      const resp = await fetch('/api/dashboard/simulate/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          api_key: apiKey || null,
          model,
          max_steps: type === 'bot' ? 8 : 5
        })
      })
      const data = await resp.json()
      if (resp.ok) {
        setStatusMessage(`Simulation ${data.simulation_id} running`)
      } else {
        setStatusMessage(data.error || 'Failed to start')
        setIsRunning(false)
      }
    } catch (e) {
      setStatusMessage(`Error: ${e.message}`)
      setIsRunning(false)
    }
  }

  const stopSimulation = async () => {
    try {
      await fetch('/api/dashboard/simulate/stop', { method: 'POST' })
      setIsRunning(false)
      setCurrentSimType(null)
      setStatusMessage('Simulation stopped')
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="simulator-panel">
      <div className="simulator-header">
        <div className="sim-title-group">
          <span className="sim-badge">TEST LAB</span>
          <h2 className="sim-main-title">Interactive Attack Simulator</h2>
          <span className="sim-hint">Trigger simulated attacks to test honeypot detection in real-time</span>
        </div>
        <div className="sim-actions-top">
          <button
            className="config-toggle-btn"
            onClick={() => setShowConfig(!showConfig)}
            title="Configure AI Agent & Model parameters"
          >
            ⚙️ AI Config {apiKey ? '✅' : ''}
          </button>
          <button
            className="reset-btn"
            onClick={onResetDatabase}
            title="Clear all honeypot database sessions"
          >
            🗑️ Reset DB
          </button>
        </div>
      </div>

      {showConfig && (
        <div className="config-drawer">
          <div className="config-row">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
              <label className="config-label" style={{ margin: 0 }}>
                LLM API Key (Groq / Gemini / OpenAI):
              </label>
              {apiKey.startsWith('gsk_') && (
                <span style={{ fontSize: '0.7rem', color: '#f59e0b', fontFamily: 'monospace', fontWeight: 'bold' }}>
                  ⚡ GROQ LPU KEY DETECTED
                </span>
              )}
              {apiKey.startsWith('AIzaSy') && (
                <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>
                  💎 GEMINI KEY DETECTED
                </span>
              )}
            </div>
            <input
              type="password"
              className="config-input"
              placeholder="Paste Groq (gsk_...) or Gemini (AIzaSy...) key"
              value={apiKey}
              onChange={handleApiKeyChange}
            />
          </div>
          <div className="config-sub-row">
            <div className="config-sub-item">
              <label className="config-sub-label">Model Provider:</label>
              <select className="config-select" value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="openai/gpt-oss-120b">openai/gpt-oss-120b (Groq - Ultra Fast)</option>
                <option value="qwen/qwen3.6-27b">qwen/qwen3.6-27b (Groq)</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash (Google Gemini)</option>
                <option value="gpt-4o-mini">gpt-4o-mini (OpenAI)</option>
              </select>
            </div>
            <div className="config-sub-item">
              <label className="config-sub-label">Max Exploit Steps:</label>
              <input
                type="number"
                min="4"
                max="15"
                className="config-number"
                value={maxSteps}
                onChange={(e) => setMaxSteps(parseInt(e.target.value) || 8)}
              />
            </div>
          </div>
        </div>
      )}

      <div className="simulator-buttons-grid">
        <button
          className={`sim-launch-card bot ${currentSimType === 'bot' && isRunning ? 'active-pulse' : ''}`}
          disabled={isRunning}
          onClick={() => launchSimulation('bot')}
        >
          <div className="sim-card-icon">🤖</div>
          <div className="sim-card-content">
            <div className="sim-card-title">1. Scripted Bot Attack</div>
            <div className="sim-card-desc">Brute-force credential stuffing • Fixed 300ms intervals • Non-adaptive mechanical hammering</div>
          </div>
          <div className="sim-card-action">Launch Attack →</div>
        </button>

        <button
          className={`sim-launch-card agent ${currentSimType === 'ai_agent' && isRunning ? 'active-pulse' : ''}`}
          disabled={isRunning}
          onClick={() => launchSimulation('ai_agent')}
        >
          <div className="sim-card-icon">🧠</div>
          <div className="sim-card-content">
            <div className="sim-card-title">2. Autonomous AI Agent Attack</div>
            <div className="sim-card-desc">
              {apiKey ? (apiKey.startsWith('gsk_') ? 'Groq LPU Reasoning' : 'Live LLM Reasoning') : 'Autonomous Reasoning Loop'} • Reads HTML comments &amp; tripwires • Exploit adaptation
            </div>
          </div>
          <div className="sim-card-action">Launch Attack →</div>
        </button>
      </div>


      {/* Live Simulation Terminal Console */}
      <div className="terminal-container">
        <div className="terminal-topbar">
          <div className="terminal-dots">
            <span className="dot red" />
            <span className="dot yellow" />
            <span className="dot green" />
          </div>
          <span className="terminal-title">
            LIVE ATTACK CONSOLE {isRunning ? `— [RUNNING: ${currentSimType?.toUpperCase()}]` : '— [IDLE]'}
          </span>
          {isRunning && (
            <button className="stop-sim-btn" onClick={stopSimulation}>
              ⏹ Stop Attack
            </button>
          )}
        </div>
        <div className="terminal-body" ref={terminalBodyRef}>
          {activeLogs.length === 0 ? (
            <div className="terminal-empty">
              Click one of the attack buttons above to start a live simulation and observe attacker telemetry in real-time.
            </div>
          ) : (
            activeLogs.map((item, idx) => (
              <div key={idx} className={`log-line log-${item.level || 'info'}`}>
                <span className="log-time">
                  {new Date(item.timestamp * 1000).toLocaleTimeString()}
                </span>
                <span className="log-msg">{item.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
