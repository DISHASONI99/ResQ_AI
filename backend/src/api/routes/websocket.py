"""
WebSocket Route - Real-time incident updates for all dashboards.

Broadcasts events to all connected clients (Public, Dispatcher, Commander).
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Connected WebSocket clients
connected_clients: List[WebSocket] = []


@router.websocket("/ws/incidents")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time incident updates.
    
    All dashboards connect here to receive:
    - new_incident: When public submits report
    - status_change: When dispatcher approves/rejects or commander updates
    - commander_assigned: When commander is auto-assigned
    """
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"🔌 WebSocket client connected. Total: {len(connected_clients)}")
    
    try:
        while True:
            # Keep connection alive, handle any incoming messages
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info(f"🔌 WebSocket client disconnected. Total: {len(connected_clients)}")


async def broadcast(event: Dict[str, Any]):
    """
    Broadcast event to all connected WebSocket clients.
    
    Event types:
    - {"type": "new_incident", "incident": {...}}
    - {"type": "status_change", "incident_id": "...", "status": "...", "commander": {...}}
    - {"type": "commander_assigned", "incident_id": "...", "commander": {...}}
    - {"type": "resolved", "incident_id": "..."}
    """
    if not connected_clients:
        logger.debug("No WebSocket clients connected, skipping broadcast")
        return
    
    message = json.dumps(event)
    disconnected = []
    
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket client: {e}")
            disconnected.append(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)
    
    logger.info(f"📡 Broadcast sent to {len(connected_clients)} clients: {event.get('type')}")


def get_connected_count() -> int:
    """Get number of connected WebSocket clients."""
    return len(connected_clients)
