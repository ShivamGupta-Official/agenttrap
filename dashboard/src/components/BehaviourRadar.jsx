import React from 'react'

const BEHAVIOURS = [
  { key: 'adaptation', label: 'Adaptation', icon: '🔄' },
  { key: 'context_usage', label: 'Context Usage', icon: '🔗' },
  { key: 'error_recovery', label: 'Error Recovery', icon: '🔧' },
  { key: 'goal_persistence', label: 'Goal Persistence', icon: '🎯' },
  { key: 'automation_pattern', label: 'Automation', icon: '⚙️' },
]

function getLevel(value) {
  if (value >= 0.7) return 'HIGH'
  if (value >= 0.35) return 'MEDIUM'
  return 'LOW'
}

function getBarColor(value) {
  if (value >= 0.7) return 'var(--agent)'
  if (value >= 0.35) return 'var(--bot)'
  return 'var(--human)'
}

export default function BehaviourRadar({ scores }) {
  if (!scores) return null

  return (
    <div className="radar-container">
      <div className="radar-title">Behavioural Analysis</div>
      <div className="behaviour-bars">
        {BEHAVIOURS.map(({ key, label, icon }) => {
          const value = scores[key] ?? 0
          const level = getLevel(value)
          return (
            <div key={key} className="behaviour-row">
              <span className="behaviour-label">{icon} {label}</span>
              <div className="behaviour-bar-bg">
                <div
                  className="behaviour-bar-fill"
                  style={{ width: `${value * 100}%`, background: getBarColor(value) }}
                />
              </div>
              <span className={`behaviour-value level-${level}`}>{level}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
