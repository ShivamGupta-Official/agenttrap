import { useState, useEffect, useRef, useCallback } from 'react'

function getDefaultWsUrl() {
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/dashboard'
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/dashboard`
}

export default function useWebSocket(customUrl) {
  const [lastEvent, setLastEvent] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef(null)
  const sseRef = useRef(null)
  const timerRef = useRef(null)
  const retriesRef = useRef(0)

  const url = customUrl || getDefaultWsUrl()

  const connectSSE = useCallback(() => {
    try {
      if (sseRef.current) {
        sseRef.current.close()
      }
      const sse = new EventSource('/api/dashboard/stream')
      sseRef.current = sse

      sse.onopen = () => {
        setIsConnected(true)
      }

      sse.onmessage = (event) => {
        try {
          if (!event.data || event.data.startsWith(':')) return
          const data = JSON.parse(event.data)
          setIsConnected(true)
          setLastEvent(data)
        } catch (e) {
          // ignore parse
        }
      }

      sse.onerror = () => {
        // SSE auto-reconnects per browser spec
      }
    } catch (e) {
      console.warn('SSE fallback failed:', e)
    }
  }, [])

  const connect = useCallback(() => {
    try {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return
      }

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        retriesRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setIsConnected(true)
          setLastEvent(data)
        } catch (e) {
          console.error('Failed to parse WS message:', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (retriesRef.current < 3) {
          retriesRef.current++
          timerRef.current = setTimeout(connect, 1000)
        } else {
          // Switch to robust HTTP SSE streaming fallback
          connectSSE()
        }
      }

      ws.onerror = () => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close()
        }
      }
    } catch (e) {
      connectSSE()
    }
  }, [url, connectSSE])

  useEffect(() => {
    connect()
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      if (wsRef.current) wsRef.current.close()
      if (sseRef.current) sseRef.current.close()
    }
  }, [connect])

  return { lastEvent, isConnected }
}

