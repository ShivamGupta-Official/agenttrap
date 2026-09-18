import React from 'react'
import SessionCard from './SessionCard'

export default function AttackerFeed({ sessions, events, selectedId, onSelect }) {
  if (sessions.length === 0) {
    return (
      <div className="empty-feed-card">
        <div className="empty-feed-icon">📡</div>
        <div className="empty-feed-text">No active sessions matching filter</div>
        <div className="empty-feed-subtext">
          Run an attack from the simulator or send traffic to the honeypot to inspect telemetry.
        </div>
      </div>
    )
  }

  return (
    <div>
      {sessions.map(session => (
        <SessionCard
          key={session.session_id}
          session={session}
          selected={session.session_id === selectedId}
          onClick={() => onSelect(session.session_id)}
        />
      ))}
    </div>
  )
}
