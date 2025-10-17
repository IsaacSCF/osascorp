from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.broadcast import manager
import uuid

router = APIRouter()

@router.websocket("/ws/orgs")
async def websocket_orgs(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # For now, just echo back or handle simple messages
            # In a real implementation, you might handle client messages here
            pass
    except WebSocketDisconnect:
        manager.disconnect(client_id)
