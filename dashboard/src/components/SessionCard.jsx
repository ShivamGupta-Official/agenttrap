import React from 'react'

function getClassification(session) {
  const c = session.agenticity?.classification || 'unknown'
  return {
    human_like:     { label: 'HUMAN',        badge: 'badge-human',   icon: '👤' },
    scripted_bot:   { label: 'BOT',          badge: 'badge-bot',     icon: '🤖' },
    likely_agentic: { label: 'AI AGENT',     badge: 'badge-agent',   icon: '🧠' },
    unknown:        { label: 'ANALYZING...', badge: 'badge-unknown', icon: '⏳' },
  }[c] || { label: 'UNKNOWN', badge: 'badge-unknown', icon: '❓' }
}

function getScoreColor(score, classification) {
  if (classification === 'likely_agentic' || score >= 60) return 'var(--agent)' // Red (AI Agent: 60-100)
  if (classification === 'scripted_bot' || score >= 16) return 'var(--bot)'     // Amber (Bot: 16-40)
  return 'var(--human)' // Green (Human: 0-15)
}

function formatDuration(first, last) {
  if (!first || !last) return '—'
  const secs = Math.round(last - first)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

export default function SessionCard({ session, selected, onClick, expanded }) {
  const cls = getClassification(session)
  const score = session.agenticity?.score ?? 0
  const classification = session.agenticity?.classification || 'unknown'
  const scoreColor = getScoreColor(score, classification)
  const ipIntel = session.ip_intel || session.agenticity?.ip_intel || null

  if (expanded) {
    return (
      <div className="expanded-card">
        <div className="expanded-header">
          <div>
            <span className={`classification-badge ${cls.badge}`}>
              {cls.icon} {cls.label}
            </span>
            <div style={{ marginTop: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Session: {session.session_id?.slice(0, 16)}
            </div>
          </div>
          <div className="expanded-score">
            <div className={`score-circle ${session.agenticity?.classification || 'unknown'}`}>
              <span className="score-number">{score}</span>
              <span className="score-label-sm">/100</span>
            </div>
          </div>
        </div>

        <div className="expanded-assessment" style={{ color: scoreColor }}>
          {session.agenticity?.assessment || 'Analyzing behaviour...'}
        </div>

        {/* IP Intelligence & Device Fingerprint Box */}
        <div className="ip-intel-box">
          <div className="ip-intel-header">
            <span className="ip-intel-title">🌐 Attacker IP &amp; Device Dossier</span>
            <span className="ip-intel-badge">
              {ipIntel?.flag || '🌐'} {ipIntel?.network_type || (session.source_ip?.startsWith('192.168.') ? 'Local Wi-Fi / LAN' : 'Remote IP')}
            </span>
          </div>

          <div className="ip-intel-grid">
            <div className="ip-intel-item">
              <span className="intel-key">Source IP</span>
              <span className="intel-val highlight-ip">{session.source_ip || '127.0.0.1'}</span>
            </div>
            <div className="ip-intel-item">
              <span className="intel-key">Origin Location</span>
              <span className="intel-val">
                {ipIntel?.flag || '📍'} {ipIntel?.city && ipIntel.city !== 'Unknown City' ? `${ipIntel.city}, ` : ''}{ipIntel?.country || (session.source_ip?.startsWith('192.168.') ? 'Local Subnet Device' : 'Unknown')}
              </span>
            </div>
            <div className="ip-intel-item">
              <span className="intel-key">ISP / Network</span>
              <span className="intel-val">{ipIntel?.isp || 'Local Network Interface'}</span>
            </div>
            <div className="ip-intel-item">
              <span className="intel-key">Device &amp; OS</span>
              <span className="intel-val">
                {ipIntel?.device?.device_icon || '💻'} {ipIntel?.device?.os || 'Unknown OS'} ({ipIntel?.device?.device_type || 'Client'})
              </span>
            </div>
            <div className="ip-intel-item full-width">
              <span className="intel-key">Client / Tool Fingerprint</span>
              <span className="intel-val mono">{ipIntel?.device?.client || 'HTTP Client'}</span>
            </div>
          </div>
        </div>

        <div className="expanded-meta">
          <div className="meta-item"><span className="meta-key">Total Packets</span><span className="meta-value">{session.request_count || 0} reqs</span></div>
          <div className="meta-item"><span className="meta-key">Attack Duration</span><span className="meta-value">{formatDuration(session.first_seen, session.last_seen)}</span></div>
          <div className="meta-item"><span className="meta-key">First Seen</span><span className="meta-value">{session.first_seen ? new Date(session.first_seen * 1000).toLocaleTimeString() : '—'}</span></div>
          <div className="meta-item"><span className="meta-key">Last Active</span><span className="meta-value">{session.last_seen ? new Date(session.last_seen * 1000).toLocaleTimeString() : '—'}</span></div>
        </div>
      </div>
    )
  }

  return (
    <div className={`session-card ${selected ? 'selected' : ''}`} onClick={onClick}>
      <div className="card-header">
        <span className={`classification-badge ${cls.badge}`}>
          {cls.icon} {cls.label}
        </span>
        <span className="session-meta">
          <span>{session.session_id?.slice(0, 8)}</span>
          <span>{session.request_count || 0} reqs</span>
        </span>
      </div>

      {/* IP & Device Pill */}
      <div className="card-ip-strip">
        <span className="ip-pill" title={`Source IP: ${session.source_ip}`}>
          {ipIntel?.flag || '🌐'} {session.source_ip || '127.0.0.1'}
        </span>
        <span className="device-pill" title={`Device: ${ipIntel?.device?.os || 'Unknown'}`}>
          {ipIntel?.device?.device_icon || '💻'} {ipIntel?.device?.os?.split(' ')[0] || 'Client'}
        </span>
      </div>

      <div className="agenticity-score">
        <div className="score-bar-bg">
          <div
            className="score-bar-fill"
            style={{ width: `${score}%`, background: scoreColor }}
          />
        </div>
        <div className="score-label">
          <span>Agenticity</span>
          <span className="score-value" style={{ color: scoreColor }}>{score}/100</span>
        </div>
      </div>
    </div>
  )
}
