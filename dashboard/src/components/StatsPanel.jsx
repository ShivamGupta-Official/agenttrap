import React from 'react'

export default function StatsPanel({ stats }) {
  const cards = [
    {
      label: 'Total Sessions',
      value: stats.total,
      icon: '📊',
      type: 'neutral',
      hint: 'Tracked visitors & bots'
    },
    {
      label: 'Human-like',
      value: stats.human,
      icon: '👤',
      type: 'human',
      hint: 'Score 0 – 15'
    },
    {
      label: 'Scripted Bots',
      value: stats.bot,
      icon: '🤖',
      type: 'bot',
      hint: 'Score 16 – 59'
    },
    {
      label: 'AI Agents',
      value: stats.agent,
      icon: '🧠',
      type: 'agent',
      hint: 'Score 60 – 100'
    },
    {
      label: 'Total Packets',
      value: stats.totalRequests,
      icon: '📡',
      type: 'neutral',
      hint: 'Inbound requests logged'
    }
  ]

  return (
    <div className="stats-panel">
      {cards.map((c, idx) => (
        <div key={idx} className={`stat-card ${c.type}`}>
          <div className="stat-card-top">
            <span className="stat-icon-wrapper">{c.icon}</span>
            <span className="stat-pill-tag">{c.hint}</span>
          </div>
          <div className="stat-value">{c.value}</div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  )
}
