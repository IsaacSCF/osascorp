import json
import redis
import os
from typing import Dict, Any
from fastapi import WebSocket
from starlette.websockets import WebSocketState

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# For development without Redis, use a simple in-memory pub/sub
try:
    import redis
    redis_available = True
except ImportError:
    redis_available = False

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        if redis_available:
            try:
                self.redis = redis.from_url(REDIS_URL)
            except:
                self.redis = None
        else:
            self.redis = None

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
            except Exception:
                disconnected_clients.append(client_id)

        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        message = json.dumps({
            "event": event_type,
            "data": data
        })
        # Publish to Redis for cross-instance communication (if available)
        if self.redis:
            try:
                self.redis.publish("orgs_events", message)
            except:
                pass  # Redis not available, continue with local broadcast
        # Broadcast to local connections
        await self.broadcast(message)

manager = ConnectionManager()

def get_redis_client():
    if redis_available:
        try:
            return redis.from_url(REDIS_URL)
        except:
            return None
    return None
