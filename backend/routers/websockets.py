from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from services.websocket_manager import manager
from routers.auth import get_current_user_ws
from typing import Dict

router = APIRouter(
    prefix="/ws",
    tags=["websockets"]
)

@router.websocket("/project/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    current_user: Dict = Depends(get_current_user_ws)
):
    try:
        await manager.connect(websocket, project_id)
        
        # Send initial connection success message
        await manager.send_personal_message(
            {
                "type": "connection_established",
                "message": "Connected to project updates"
            },
            websocket
        )
        
        try:
            while True:
                # Wait for messages from the client
                data = await websocket.receive_json()
                
                # Handle different types of messages
                if data["type"] == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, project_id)
            await manager.broadcast_to_project(
                project_id,
                {
                    "type": "client_disconnected",
                    "message": f"Client #{id(websocket)} disconnected"
                }
            )
    except Exception as e:
        await websocket.close(code=1000)
        raise e 