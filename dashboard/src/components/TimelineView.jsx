import React from 'react'

function getDotClass(event) {
  const t = event.event_type || ''
  if (t.includes('probe') || t.includes('error')) return 'probe'
  if (t.includes('strategy') || t.includes('adapt')) return 'strategy'
  if (t.includes('tripwire')) return 'tripwire'
  return ''
}

function getEventIcon(event) {
  const t = event.event_type || ''
  if (t.includes('tripwire')) return '🎯'
  if (t.includes('probe') || t.includes('error')) return '⚠️'
  if (t.includes('strategy')) return '🔄'
  if (t.includes('context')) return '🔗'
  if (t.includes('goal')) return '🎯'
  return '📍'
}

export default function TimelineView({ events }) {
  if (!events || events.length === 0) return null

  return (
    <div className="timeline-container">
      <div className="timeline-title">📋 Session Timeline</div>
      <ul className="timeline-list">
        {events.map((event, i) => (
          <li key={i} className="timeline-item">
            <span className={`timeline-dot ${getDotClass(event)}`} />
            <div className="timeline-content">
              <div className="timeline-time">
                {event.timestamp ? new Date(event.timestamp * 1000).toLocaleTimeString() : '—'}
                {' '}
                <span style={{ color: 'var(--text-secondary)' }}>
                  {getEventIcon(event)} {event.event_type?.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="timeline-detail">
                {event.detail || `${event.previous_action || ''} → ${event.current_action || ''}`}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
