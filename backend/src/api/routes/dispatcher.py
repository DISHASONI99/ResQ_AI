"""
Dispatcher API Routes - Incident review and approval workflow.

Endpoints for dispatchers to:
- View pending incident queue
- Approve incidents (auto-assigns commander)
- Reject fake/invalid reports
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import logging

from src.services.postgres_service import get_postgres_client
from src.services.commander_service import (
    get_available_commander, 
    assign_commander,
    get_all_commanders
)
from src.services.sop_service import get_safety_guidelines, get_eta_message
from src.api.routes.websocket import broadcast

logger = logging.getLogger(__name__)
router = APIRouter()


class ApproveRequest(BaseModel):
    """Request body for approving an incident."""
    priority: Optional[str] = None  # Override priority if needed
    assets: Optional[List[str]] = None  # Override assets if needed
    notes: Optional[str] = None  # Dispatcher notes


class RejectRequest(BaseModel):
    """Request body for rejecting an incident."""
    reason: str


@router.get("/queue")
async def get_pending_incidents():
    """
    Get all incidents pending dispatcher review.
    
    Returns incidents with status='pending_dispatch' ordered by creation time.
    """
    try:
        conn = await get_postgres_client()
        incidents = await conn.fetch(
            """
            SELECT incident_id, session_id, priority, incident_type, 
                   location, address, recommended_assets, reasoning, 
                   status, created_at
            FROM incidents 
            WHERE status = 'pending_dispatch'
            ORDER BY 
                CASE priority 
                    WHEN 'P1' THEN 1 
                    WHEN 'P2' THEN 2 
                    WHEN 'P3' THEN 3 
                    WHEN 'P4' THEN 4 
                END,
                created_at DESC
            """
        )
        
        return {
            "count": len(incidents),
            "incidents": [dict(i) for i in incidents]
        }
    except Exception as e:
        logger.error(f"Failed to get pending queue: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")


@router.get("/commanders")
async def get_commanders():
    """Get all commanders with their current status."""
    commanders = get_all_commanders()
    return {
        "count": len(commanders),
        "commanders": commanders
    }


@router.post("/{incident_id}/approve")
async def approve_incident(incident_id: str, request: Optional[ApproveRequest] = None):
    """
    Approve incident and auto-assign commander.
    
    Flow:
    1. Update incident status to 'dispatched'
    2. Find available commander (matching specialization if possible)
    3. Assign commander and update incident
    4. Broadcast WebSocket event to all dashboards
    5. Return commander details for public messaging
    """
    try:
        conn = await get_postgres_client()
        
        # Get incident details
        incident = await conn.fetchrow(
            "SELECT * FROM incidents WHERE incident_id = $1",
            incident_id
        )
        
        if not incident:
            raise HTTPException(404, f"Incident {incident_id} not found")
        
        if incident["status"] != "pending_dispatch":
            raise HTTPException(400, f"Incident already processed (status: {incident['status']})")
        
        # Find available commander
        incident_type = incident["incident_type"]
        commander = get_available_commander(incident_type)
        
        if not commander:
            raise HTTPException(503, "No commanders available")
        
        # Assign commander
        assign_commander(commander["id"], incident_id)
        
        # Determine final priority and assets
        final_priority = request.priority if request and request.priority else incident["priority"]
        final_assets = request.assets if request and request.assets else incident["recommended_assets"]
        
        # Update incident in database
        await conn.execute(
            """
            UPDATE incidents 
            SET status = 'dispatched', 
                assigned_commander = $1,
                priority = $2,
                recommended_assets = $3,
                dispatched_at = NOW()
            WHERE incident_id = $4
            """,
            commander["id"],
            final_priority,
            final_assets,
            incident_id
        )
        
        
        # Get safety guidelines for public message
        safety_tips = get_safety_guidelines(incident_type)
        eta_message = get_eta_message(incident_type)
        
        # Broadcast to all dashboards
        await broadcast({
            "type": "commander_assigned",
            "incident_id": incident_id,
            "status": "dispatched",
            "commander": {
                "id": commander["id"],
                "name": commander["name"],
                "phone": commander["phone"],
                "zone": commander["zone"]
            },
            "priority": final_priority,
            "assets": final_assets
        })
        
        logger.info(f"✅ Incident {incident_id} approved, assigned to {commander['name']}")
        
        # Build public notification message
        public_message = f"""🚨 **मदद आ रही है! / Help is on the way!**

👮 **कमांडर / Commander:** {commander['name']}
📞 **संपर्क / Contact:** {commander['phone']}
🏢 **ज़ोन / Zone:** {commander['zone']}

🚑 **भेजे गए संसाधन / Dispatched Assets:**
{', '.join(final_assets) if isinstance(final_assets, list) else final_assets}

⏱️ {eta_message}

{safety_tips}

शांत रहें। सहायता मार्ग में है।
Stay calm. Help is en route."""
        
        return {
            "status": "approved",
            "incident_id": incident_id,
            "commander": {
                "id": commander["id"],
                "name": commander["name"],
                "phone": commander["phone"],
                "zone": commander["zone"]
            },
            "priority": final_priority,
            "assets": final_assets,
            "public_message": public_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve incident: {e}")
        raise HTTPException(500, f"Approval failed: {str(e)}")


@router.post("/{incident_id}/reject")
async def reject_incident(incident_id: str, request: RejectRequest):
    """
    Reject incident as fake or invalid.
    
    Updates status to 'rejected' and broadcasts to dashboards.
    """
    try:
        conn = await get_postgres_client()
        
        # Check incident exists
        incident = await conn.fetchrow(
            "SELECT * FROM incidents WHERE incident_id = $1",
            incident_id
        )
        
        if not incident:
            raise HTTPException(404, f"Incident {incident_id} not found")
        
        # Update status
        await conn.execute(
            """
            UPDATE incidents 
            SET status = 'rejected',
                reasoning = reasoning || E'\n\n[REJECTED: ' || $1 || ']'
            WHERE incident_id = $2
            """,
            request.reason,
            incident_id
        )
        
        
        # Broadcast rejection
        await broadcast({
            "type": "status_change",
            "incident_id": incident_id,
            "status": "rejected",
            "reason": request.reason
        })
        
        logger.info(f"❌ Incident {incident_id} rejected: {request.reason}")
        
        return {
            "status": "rejected",
            "incident_id": incident_id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject incident: {e}")
        raise HTTPException(500, f"Rejection failed: {str(e)}")
