import React from 'react'

function getEvidenceIcon(text) {
  const lower = text.toLowerCase()
  if (lower.includes('tripwire') || lower.includes('triggered')) return '🎯'
  if (lower.includes('changed') || lower.includes('strategy') || lower.includes('adapt')) return '🔄'
  if (lower.includes('error') || lower.includes('failed') || lower.includes('recovery')) return '🔧'
  if (lower.includes('context') || lower.includes('followed') || lower.includes('information')) return '🔗'
  if (lower.includes('goal') || lower.includes('persist') || lower.includes('objective')) return '🎯'
  if (lower.includes('timing') || lower.includes('burst') || lower.includes('automation')) return '⏱️'
  if (lower.includes('llm') || lower.includes('artifact') || lower.includes('pattern')) return '📝'
  if (lower.includes('score') || lower.includes('breakdown')) return '📊'
  if (lower.includes('bonus')) return '⭐'
  return '•'
}

export default function EvidencePanel({ evidence }) {
  if (!evidence || evidence.length === 0) return null

  return (
    <div className="evidence-panel">
      <div className="evidence-title">🔎 Evidence &amp; Reasoning</div>
      <ul className="evidence-list">
        {evidence.map((item, i) => (
          <li key={i} className="evidence-item">
            <span className="evidence-icon">{getEvidenceIcon(item)}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
