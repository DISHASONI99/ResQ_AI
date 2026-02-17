"""
Commander API Routes - Field operations management.

Endpoints for commanders to:
- View active/assigned incidents
- Update incident status
- Request reinforcement
- Mark incidents as resolved
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from enum import Enum
import logging

from src.services.postgres_service import get_postgres_client
from src.services.commander_service import release_commander, get_commander_by_id
from src.api.routes.websocket import broadcast

logger = logging.getLogger(__name__)
router = APIRouter()


class IncidentStatus(str, Enum):
    """Valid status values for commander updates."""
    in_progress = "in_progress"
    reinforcement = "reinforcement"
    escalated = "escalated"
    resolved = "resolved"


class StatusUpdateRequest(BaseModel):
    """Request body for updating incident status."""
    status: IncidentStatus
    notes: Optional[str] = None


@router.get("/active")
async def get_active_incidents(commander_id: Optional[str] = Query(None)):
    """
    Get active incidents for commander view.
    
    Args:
        commander_id: Optional - filter by assigned commander
        
    Returns incidents with status in ('dispatched', 'in_progress', 'reinforcement', 'escalated')
    """
    try:
        conn = await get_postgres_client()
        
        if commander_id:
            incidents = await conn.fetch(
                """
                SELECT incident_id, session_id, priority, incident_type,
                       location, address, recommended_assets, reasoning,
                       status, assigned_commander, created_at, dispatched_at
                FROM incidents 
                WHERE status IN ('dispatched', 'in_progress', 'reinforcement', 'escalated')
                  AND assigned_commander = $1
                ORDER BY 
                    CASE priority 
                        WHEN 'P1' THEN 1 
                        WHEN 'P2' THEN 2 
                        WHEN 'P3' THEN 3 
                        WHEN 'P4' THEN 4 
                    END,
                    dispatched_at DESC
                """,
                commander_id
            )
        else:
            incidents = await conn.fetch(
                """
                SELECT incident_id, session_id, priority, incident_type,
                       location, address, recommended_assets, reasoning,
                       status, assigned_commander, created_at, dispatched_at
                FROM incidents 
                WHERE status IN ('dispatched', 'in_progress', 'reinforcement', 'escalated')
                ORDER BY 
                    CASE priority 
                        WHEN 'P1' THEN 1 
                        WHEN 'P2' THEN 2 
                        WHEN 'P3' THEN 3 
                        WHEN 'P4' THEN 4 
                    END,
                    dispatched_at DESC
                """
            )
        
        
        # Enrich with commander details
        enriched = []
        for inc in incidents:
            inc_dict = dict(inc)
            if inc_dict.get("assigned_commander"):
                cmd = get_commander_by_id(inc_dict["assigned_commander"])
                if cmd:
                    inc_dict["commander_details"] = {
                        "name": cmd["name"],
                        "phone": cmd["phone"],
                        "zone": cmd["zone"]
                    }
            enriched.append(inc_dict)
        
        return {
            "count": len(enriched),
            "incidents": enriched
        }
        
    except Exception as e:
        logger.error(f"Failed to get active incidents: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")


@router.post("/{incident_id}/status")
async def update_incident_status(incident_id: str, request: StatusUpdateRequest):
    """
    Update incident status.
    
    Valid statuses:
    - in_progress: Teams en route or on scene
    - reinforcement: Additional resources requested
    - escalated: Priority upgraded
    - resolved: Incident contained
    """
    try:
        conn = await get_postgres_client()
        
        # Get incident
        incident = await conn.fetchrow(
            "SELECT * FROM incidents WHERE incident_id = $1",
            incident_id
        )
        
        if not incident:
            raise HTTPException(404, f"Incident {incident_id} not found")
        
        old_status = incident["status"]
        new_status = request.status.value
        
        # Handle priority escalation
        new_priority = incident["priority"]
        if new_status == "escalated":
            priority_upgrade = {"P4": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}
            new_priority = priority_upgrade.get(incident["priority"], "P1")
        
        # Update incident
        if request.notes:
            await conn.execute(
                """
                UPDATE incidents 
                SET status = $1,
                    priority = $2,
                    reasoning = reasoning || E'\n\n[' || $1 || ': ' || $3 || ']',
                    resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE NULL END
                WHERE incident_id = $4
                """,
                new_status,
                new_priority,
                request.notes,
                incident_id
            )
        else:
            await conn.execute(
                """
                UPDATE incidents 
                SET status = $1,
                    priority = $2,
                    resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE NULL END
                WHERE incident_id = $3
                """,
                new_status,
                new_priority,
                incident_id
            )
        
        # Release commander if resolved
        if new_status == "resolved" and incident["assigned_commander"]:
            release_commander(incident["assigned_commander"])
        
        
        # Build public message based on status
        status_messages = {
            "in_progress": "📍 **स्थिति / Status Update**\n\nटीम घटनास्थल पर पहुंच गई है।\nTeams have arrived on scene.\n\nसहायता जारी है। शांत रहें।\nAssistance in progress. Stay calm.",
            "reinforcement": "🆘 **अतिरिक्त सहायता / Reinforcement Requested**\n\nअतिरिक्त संसाधन भेजे जा रहे हैं।\nAdditional resources are being dispatched.\n\nकृपया प्रतीक्षा करें।\nPlease hold on.",
            "escalated": "⚠️ **प्राथमिकता बढ़ाई गई / Priority Escalated**\n\nआपके मामले की प्राथमिकता बढ़ा दी गई है।\nYour case priority has been upgraded.\n\nतेज़ प्रतिक्रिया आ रही है।\nFaster response incoming.",
            "resolved": "✅ **समाधान / Incident Resolved**\n\nआपकी घटना का समाधान हो गया है।\nYour incident has been resolved.\n\nResQ AI का उपयोग करने के लिए धन्यवाद।\nThank you for using ResQ AI.\n\nसुरक्षित रहें! 🙏\nStay safe!"
        }
        
        public_message = status_messages.get(new_status, f"Status updated to: {new_status}")
        
        # Get commander details if assigned
        commander_info = None
        if incident["assigned_commander"]:
            cmd = get_commander_by_id(incident["assigned_commander"])
            if cmd:
                commander_info = {
                    "name": cmd["name"],
                    "phone": cmd["phone"],
                    "zone": cmd["zone"]
                }

        # Broadcast update
        await broadcast({
            "type": "status_change",
            "incident_id": incident_id,
            "old_status": old_status,
            "status": new_status,
            "priority": new_priority,
            "notes": request.notes,
            "public_message": public_message,
            "commander_info": commander_info
        })
        
        logger.info(f"📋 Incident {incident_id} status: {old_status} → {new_status}")
        
        return {
            "incident_id": incident_id,
            "old_status": old_status,
            "status": new_status,
            "priority": new_priority,
            "public_message": public_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(500, f"Status update failed: {str(e)}")


@router.get("/history")
async def get_resolved_incidents(limit: int = Query(20, ge=1, le=100)):
    """Get recently resolved incidents for reference."""
    try:
        conn = await get_postgres_client()
        
        incidents = await conn.fetch(
            """
            SELECT incident_id, priority, incident_type, address,
                   status, assigned_commander, created_at, resolved_at
            FROM incidents 
            WHERE status = 'resolved'
            ORDER BY resolved_at DESC
            LIMIT $1
            """,
            limit
        )
        
        
        return {
            "count": len(incidents),
            "incidents": [dict(i) for i in incidents]
        }
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")
