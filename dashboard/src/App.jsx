import React, { useState, useEffect, useCallback } from 'react'
import useWebSocket from './hooks/useWebSocket'
import StatsPanel from './components/StatsPanel'
import AttackerFeed from './components/AttackerFeed'
import SessionCard from './components/SessionCard'
import BehaviourRadar from './components/BehaviourRadar'
import EvidencePanel from './components/EvidencePanel'
import TimelineView from './components/TimelineView'
import AttackSimulatorPanel from './components/AttackSimulatorPanel'

export default function App() {
  const [sessions, setSessions] = useState({})
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [events, setEvents] = useState([])
  const [simulationLogs, setSimulationLogs] = useState([])
  const [isDataSynced, setIsDataSynced] = useState(false)
  const { lastEvent, isConnected: isWsConnected } = useWebSocket()

  // Detect if user opened the dedicated Attack Simulator page
  const pathname = typeof window !== 'undefined' ? window.location.pathname : ''
  const isSimulatorOnlyMode = pathname.startsWith('/simulator') || pathname.startsWith('/attack-lab')

  // Fetch initial sessions on mount and keep syncing
  const fetchSessions = useCallback(() => {
    fetch('/api/dashboard/sessions')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          const map = {}
          data.forEach(s => { map[s.session_id] = s })
          setSessions(map)
          setIsDataSynced(true)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchSessions()
    const interval = setInterval(fetchSessions, 1500)
    return () => clearInterval(interval)
  }, [fetchSessions])

  // Process live stream events
  useEffect(() => {
    if (!lastEvent) return

    setIsDataSynced(true)
    const { event_type, session, log } = lastEvent

    if (event_type === 'simulation_log' && log) {
      setSimulationLogs(prev => [...prev, log].slice(-300))
    } else if (event_type === 'database_reset') {
      setSessions({})
      setSelectedSessionId(null)
      setEvents([])
      setSimulationLogs(prev => [...prev, {
        timestamp: Date.now() / 1000,
        message: '🗑️ Honeypot Database reset. Ready for fresh demonstration.',
        level: 'warn'
      }])
    } else if (session) {
      setSessions(prev => ({
        ...prev,
        [session.session_id]: session
      }))
      setSelectedSessionId(current => current || session.session_id)
    }

    if (event_type !== 'simulation_log') {
      setEvents(prev => [lastEvent, ...prev].slice(0, 200))
    }
  }, [lastEvent])

  const handleResetDatabase = async () => {
    if (window.confirm('Reset all honeypot sessions and probe states?')) {
      try {
        await fetch('/api/dashboard/reset', { method: 'POST' })
        setSessions({})
        setSelectedSessionId(null)
        setEvents([])
      } catch (e) {
        console.error('Reset error:', e)
      }
    }
  }

  const [activeFilter, setActiveFilter] = useState('all')

  const isLive = isWsConnected || isDataSynced
  const selectedSession = selectedSessionId ? sessions[selectedSessionId] : null
  const allSessions = Object.values(sessions).sort((a, b) => (b.last_seen || 0) - (a.last_seen || 0))
  
  const filteredSessions = allSessions.filter(s => {
    if (activeFilter === 'all') return true
    if (activeFilter === 'agent') return s.agenticity?.classification === 'likely_agentic'
    if (activeFilter === 'bot') return s.agenticity?.classification === 'scripted_bot'
    if (activeFilter === 'human') return s.agenticity?.classification === 'human_like'
    return true
  })

  const stats = {
    total: allSessions.length,
    human: allSessions.filter(s => s.agenticity?.classification === 'human_like').length,
    bot: allSessions.filter(s => s.agenticity?.classification === 'scripted_bot').length,
    agent: allSessions.filter(s => s.agenticity?.classification === 'likely_agentic').length,
    dos: allSessions.filter(s => s.agenticity?.classification === 'dos_flood').length,
    ddos: allSessions.filter(s => s.agenticity?.classification === 'ddos_flood').length,
    unknown: allSessions.filter(s => !s.agenticity || s.agenticity?.classification === 'unknown').length,
    totalRequests: allSessions.reduce((sum, s) => sum + (s.request_count || 0), 0),
  }

  // -------------------------------------------------------------------------
  // RENDER DEDICATED ATTACK SIMULATOR STANDALONE PORTAL
  // -------------------------------------------------------------------------
  if (isSimulatorOnlyMode) {
    return (
      <div className="app">
        <header className="header">
          <div className="header-left">
            <div className="logo-badge">
              <span className="logo-pulse"></span>
              <span className="logo-emoji">🍯</span>
            </div>
            <div>
              <h1>ARE YOU EVEN HUMAN?</h1>
              <p className="subtitle">Attack Simulator Lab — Multi-Vector Probe Engine</p>
            </div>
          </div>

          <div className="header-right">
            <a
              href="/dashboard"
              target="_blank"
              rel="noreferrer"
              className="action-btn primary"
            >
              🛡️ Live SOC Console ↗
            </a>
            <a
              href="/login"
              target="_blank"
              rel="noreferrer"
              className="action-btn secondary"
            >
              🚪 Open Decoy ↗
            </a>
            <span className={`connection-status ${isLive ? 'connected' : 'disconnected'}`}>
              <span className="status-dot" />
              {isLive ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
        </header>

        <StatsPanel stats={stats} />

        <div className="simulator-tab-container" style={{ padding: '0 1.5rem 1.5rem 1.5rem' }}>
          <AttackSimulatorPanel
            simulationLogs={simulationLogs}
            isConnected={isLive}
            onResetDatabase={handleResetDatabase}
            onClearLogs={() => setSimulationLogs([])}
          />
        </div>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // RENDER PURE SOC LIVE MONITOR DASHBOARD (DEMO DISPLAY FOR JUDGES)
  // -------------------------------------------------------------------------
  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo-badge">
            <span className="logo-pulse"></span>
            <span className="logo-emoji">🍯</span>
          </div>
          <div>
            <h1>ARE YOU EVEN HUMAN?</h1>
            <p className="subtitle">Autonomous AI-Attacker Honeypot &amp; Threat Forensics Center</p>
          </div>
        </div>

        <div className="header-nav-tabs" style={{ display: 'flex', gap: '0.4rem', background: 'rgba(15, 23, 42, 0.6)', padding: '0.25rem 0.35rem', borderRadius: '9999px', border: '1px solid var(--border-subtle)' }}>
          <button
            style={{ padding: '0.4rem 0.9rem', borderRadius: '9999px', border: 'none', background: !isSimulatorOnlyMode ? 'rgba(56, 189, 248, 0.25)' : 'transparent', color: !isSimulatorOnlyMode ? '#fff' : 'var(--text-secondary)', fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer' }}
            onClick={() => window.history.pushState({}, '', '/dashboard')}
          >
            🛡️ Live SOC
          </button>
          <button
            style={{ padding: '0.4rem 0.9rem', borderRadius: '9999px', border: 'none', background: isSimulatorOnlyMode ? 'rgba(56, 189, 248, 0.25)' : 'transparent', color: isSimulatorOnlyMode ? '#fff' : 'var(--text-secondary)', fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer' }}
            onClick={() => window.history.pushState({}, '', '/simulator')}
          >
            ⚡ Attack Lab
          </button>
        </div>

        <div className="header-right">
          <a
            href="/"
            className="action-btn simulator"
            title="Open Master Showcase Landing Page"
          >
            🌟 Master Showcase ↗
          </a>
          <a
            href="/login"
            target="_blank"
            rel="noreferrer"
            className="action-btn secondary"
            title="Open Honeypot Decoy Portal in a new tab"
          >
            🚪 Decoy Portal ↗
          </a>
          <button
            onClick={handleResetDatabase}
            className="action-btn ghost"
            title="Reset telemetry database"
          >
            🗑️ Reset
          </button>
          <span className={`connection-status ${isLive ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            {isLive ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </header>

      <StatsPanel stats={stats} />

      <div className="main-content">
        <div className="feed-panel">
          <div className="panel-header-row">
            <div>
              <h2 className="panel-title">🛡️ Live Attacker Feed</h2>
              <span className="panel-subtitle">Classified by Agentic Behavioral Signatures</span>
            </div>
            <div className="filter-tab-group">
              <button
                className={`filter-btn ${activeFilter === 'all' ? 'active' : ''}`}
                onClick={() => setActiveFilter('all')}
              >
                All ({allSessions.length})
              </button>
              <button
                className={`filter-btn agent ${activeFilter === 'agent' ? 'active' : ''}`}
                onClick={() => setActiveFilter('agent')}
              >
                AI ({stats.agent})
              </button>
              <button
                className={`filter-btn bot ${activeFilter === 'bot' ? 'active' : ''}`}
                onClick={() => setActiveFilter('bot')}
              >
                Bots ({stats.bot})
              </button>
              <button
                className={`filter-btn human ${activeFilter === 'human' ? 'active' : ''}`}
                onClick={() => setActiveFilter('human')}
              >
                Humans ({stats.human})
              </button>
            </div>
          </div>

          <AttackerFeed
            sessions={filteredSessions}
            events={events}
            selectedId={selectedSessionId}
            onSelect={setSelectedSessionId}
          />
        </div>

        <div className="detail-panel">
          {selectedSession ? (
            <>
              <div className="panel-header-row">
                <h2 className="panel-title">Attacker Profile Analysis</h2>
                <span className="panel-subtitle">Session: {selectedSession.session_id?.slice(0, 12)}</span>
              </div>
              <SessionCard session={selectedSession} expanded />
              {selectedSession.agenticity?.behaviour_scores && (
                <BehaviourRadar scores={selectedSession.agenticity.behaviour_scores} />
              )}
              {selectedSession.agenticity?.evidence && (
                <EvidencePanel evidence={selectedSession.agenticity.evidence} />
              )}
              {selectedSession.events && selectedSession.events.length > 0 && (
                <TimelineView events={selectedSession.events} />
              )}
            </>
          ) : (
            <div className="empty-detail">
              <div className="radar-scanner-wrapper">
                <div className="radar-circle circle-1"></div>
                <div className="radar-circle circle-2"></div>
                <div className="radar-circle circle-3"></div>
                <div className="radar-beam"></div>
                <div className="radar-core-icon">🎯</div>
              </div>
              <h3 className="empty-heading">Awaiting Inbound Adversary Probes</h3>
              <p className="empty-subtext">
                The honeypot telemetry engine is actively listening for automated scanners, credential stuffers, and autonomous LLM agents.
              </p>
              <div className="empty-action-group">
                <a
                  href="/simulator"
                  target="_blank"
                  rel="noreferrer"
                  className="action-btn simulator pulse-btn"
                >
                  ⚡ Trigger Test Attack Simulation ↗
                </a>
                <a
                  href="/login"
                  target="_blank"
                  rel="noreferrer"
                  className="action-btn secondary"
                >
                  🚪 Interact with Decoy Portal ↗
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
