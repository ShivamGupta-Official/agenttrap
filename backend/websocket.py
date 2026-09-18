import asyncio
from fastapi import WebSocket
import json

class ConnectionManager:
    """Manages WebSocket and SSE connections for live dashboard updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.sse_queues: list[asyncio.Queue] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    def subscribe_sse(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.sse_queues.append(q)
        return q
        
    def unsubscribe_sse(self, q: asyncio.Queue):
        if q in self.sse_queues:
            self.sse_queues.remove(q)
    
    async def broadcast(self, data: dict):
        """Broadcast data to all connected WebSocket and SSE clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)
            
        for q in list(self.sse_queues):
            try:
                await q.put(data)
            except Exception:
                pass

manager = ConnectionManager()

