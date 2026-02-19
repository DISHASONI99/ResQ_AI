"""
Incidents API - Core endpoint for emergency incident processing
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from pydantic import BaseModel
from typing import Optional, Literal
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class IncidentRequest(BaseModel):
    """Request model for creating an incident."""
    text: str
    role: Literal["dispatcher", "commander", "public"] = "dispatcher"
    location: Optional[dict] = None  # {"lat": float, "lon": float}


class IncidentResponse(BaseModel):
    """Response model for incident processing."""
    incident_id: str
    status: str
    priority: Optional[str] = None
    incident_type: Optional[str] = None
    recommended_assets: Optional[list] = None
    reasoning: Optional[str] = None
    requires_approval: bool = False
    retrieved_docs: Optional[list] = None


@router.post("/", response_model=IncidentResponse)
async def create_incident(
    request: Request,
    incident: IncidentRequest,
):
    """
    Create and process a new emergency incident.
    
    This endpoint:
    1. Accepts text input (and optionally location)
    2. Generates embeddings via FastEmbed
    3. Performs hybrid search on Qdrant
    """
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    
    # Get services from app state
    qdrant_service = request.app.state.qdrant
    llm_service = request.app.state.llm
    
    # 1. Analyze incident with LLM
    system_prompt = """You are an Emergency Response AI. Analyze the user's incident report and respond ONLY with a valid JSON object.

Your response MUST be a valid JSON object with exactly these fields:
{
  "priority": "P1 or P2 or P3 or P4",
  "incident_type": "Fire or Medical or Flood or Accident or Other",
  "reasoning": "Brief explanation of your assessment",
  "recommended_assets": ["list", "of", "assets"]
}

Priority levels:
- P1 (Critical): Life-threatening, immediate response required
- P2 (High): Serious situation, urgent response needed
- P3 (Medium): Important but not immediately life-threatening
- P4 (Low): Minor incident, can be scheduled

Output ONLY the JSON object, no additional text."""
    
    try:
        llm_result = await llm_service.generate(
            user_prompt=incident.text,
            system_prompt=system_prompt,
            response_format={"type": "json_object"}
        )
        
        # Parse LLM JSON response
        analysis = json.loads(llm_result["content"])
        
        priority = analysis.get("priority", "P3")
        incident_type = analysis.get("incident_type", "Unknown")
        reasoning = analysis.get("reasoning", "Analyzed by ResQ AI")
        assets = analysis.get("recommended_assets", [])
        
        # Save incident to PostgreSQL (required for approval FK constraint)
        from src.services.postgres_service import save_incident
        await save_incident(
            incident_id=incident_id,
            session_id=None,
            priority=priority,
            incident_type=incident_type,
            location=incident.location or {},
            address="",
            recommended_assets=[{"type": a} for a in assets] if assets else [],
            critical_instructions=reasoning,
            reasoning=reasoning,
        )
        
        return IncidentResponse(
            incident_id=incident_id,
            status="analyzed",
            priority=priority,
            incident_type=incident_type,
            recommended_assets=assets,
            reasoning=reasoning,
            requires_approval=True,
            retrieved_docs=[],
        )
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        # Fallback to stub if LLM fails
        return IncidentResponse(
            incident_id=incident_id,
            status="processing",
            priority="P3",
            incident_type="Pending",
            recommended_assets=[],
            reasoning=f"Automated analysis failed: {str(e)}",
            requires_approval=True,
            retrieved_docs=[],
        )


@router.post("/multimodal", response_model=IncidentResponse)
async def create_multimodal_incident(
    request: Request,
    text: Optional[str] = Form(default=""),
    role: str = Form(default="dispatcher"),
    audio: Optional[UploadFile] = File(default=None),
    image: Optional[UploadFile] = File(default=None),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
):
    """
    Create incident with multimodal inputs (audio, image, location).
    
    TRUE MULTIMODAL PROCESSING:
    - Audio: Transcribed via Groq Whisper API
    - Image: Embedded via CLIP, searched against visual_evidence collection
    - Combined context sent to LLM for classification
    """
    from src.services.whisper_service import transcribe_audio
    
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    
    # Get services from app state
    qdrant_service = request.app.state.qdrant
    llm_service = request.app.state.llm
    embedding_service = request.app.state.embedding
    
    audio_transcript = None
    image_category = None
    image_embeddings = None
    
    # ============ PROCESS AUDIO ============
    if audio:
        try:
            audio_bytes = await audio.read()
            audio_transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.wav")
            logger.info(f"🎤 Audio transcribed: {audio_transcript[:100]}...")
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            audio_transcript = None
    
    # ============ PROCESS IMAGE ============
    if image:
        try:
            image_bytes = await image.read()
            
            # Generate CLIP embedding
            image_embeddings = embedding_service.embed_image_from_bytes(image_bytes)
            logger.info(f"🖼️ Image embedded: {len(image_embeddings)}-dim vector")
            
            # Search visual_evidence for similar disaster images
            matches = await qdrant_service.hybrid_search(
                collection="visual_evidence",
                dense_vector=image_embeddings,
                top_k=3,
            )
            
            if matches:
                # Extract category from top match
                top_match = matches[0]
                image_category = top_match.get("payload", {}).get("category", "unknown")
                confidence = top_match.get("score", 0)
                logger.info(f"🔍 Visual match: {image_category} (confidence: {confidence:.2f})")
            else:
                logger.info("⚠️ No visual matches found")
                image_category = None
                
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            image_category = None
    
    # ============ BUILD COMBINED QUERY ============
    query_parts = []
    
    # Add visual context if detected
    if image_category:
        query_parts.append(f"[VISUAL DETECTION: {image_category.upper()} incident detected from uploaded image]")
    
    # Add audio transcript
    if audio_transcript and not audio_transcript.startswith("["):
        query_parts.append(f"[AUDIO TRANSCRIPT: {audio_transcript}]")
    
    # Add user text
    query_parts.append(f"User report: {text}")
    
    # Add location if provided
    location = None
    if lat and lon:
        location = {"lat": lat, "lon": lon}
        query_parts.append(f"[LOCATION: {lat}, {lon}]")
    
    full_query = "\n".join(query_parts)
    logger.info(f"📝 Combined query:\n{full_query}")
    
    # ============ ORCHESTRATOR WORKFLOW ============
    # Use full multi-agent workflow (Supervisor → Triage → Geo → Protocol → Reflector)
    from src.graph.orchestrator import Orchestrator
    
    try:
        # Initialize orchestrator with services
        orchestrator = Orchestrator(
            qdrant_service=qdrant_service,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        
        # Run full workflow
        result = await orchestrator.process_incident(
            incident_id=incident_id,
            query=full_query,
            text_input=text,
            channel="web",
            user_role=role,
            location=location,
            audio_transcript=audio_transcript,
            image_embeddings=[image_embeddings] if image_embeddings else None,
        )
        
        logger.info(f"✅ Orchestrator result: mode={result.get('mode')}, priority={result.get('priority')}")
        
        # Extract results from workflow
        priority = result.get("priority", "P3")
        
        # CRITICAL: Visual detection OVERRIDES LLM when image shows clear disaster
        # This prevents text like "water" from overriding a clear fire image
        # Categories include both parent folders AND subfolders from Disaster_Dataset
        # Subfolders: Urban_Fire, Wild_Fire, Earthquake, Infrastructure, Land_Slide, Drought, human, sea, etc.
        
        # Map ALL possible category names (including subfolders) to incident types
        visual_type_map = {
            # Fire (parent and subfolders)
            "fire_disaster": "Fire",
            "urban_fire": "Fire",
            "wild_fire": "Fire",
            # Water
            "water_disaster": "Flood",
            # Medical/Human
            "human_damage": "Medical",
            "human": "Medical",
            # Land disasters
            "land_disaster": "Landslide",
            "land_slide": "Landslide",
            "drought": "Drought",
            # Infrastructure
            "damaged_infrastructure": "Infrastructure",
            "infrastructure": "Infrastructure",
            "earthquake": "Earthquake",
        }
        
        image_category_lower = image_category.lower() if image_category else ""
        
        if image_category_lower in visual_type_map:
            incident_type = visual_type_map[image_category_lower]
            logger.info(f"🔥 VISUAL OVERRIDE: Using {incident_type} from image (detected: {image_category}) instead of LLM")
            # Upgrade priority for fire/medical detected visually
            if incident_type in ["Fire", "Medical", "Earthquake"] and priority in ["P3", "P4"]:
                priority = "P2"
                logger.info(f"⬆️ Priority upgraded to P2 due to visual detection")
        else:
            incident_type = result.get("incident_type", "Unknown")
        
        assets = result.get("recommended_assets", [])
        reasoning = result.get("reasoning", result.get("critical_instructions", "Multi-agent analysis complete"))
        
        # Add visual override note to reasoning if applicable
        if image_category:
            reasoning = f"[VISUAL: {image_category.upper()} detected] {reasoning}"
        
        requires_approval = result.get("requires_human_approval", priority in ["P1", "P2"])
        
        # Format assets for response
        if assets and isinstance(assets[0], dict):
            formatted_assets = [f"{a.get('type', 'Unit')} x{a.get('quantity', 1)}" for a in assets]
        else:
            formatted_assets = assets or []
        
        # Save incident to PostgreSQL (required for approval FK constraint)
        from src.services.postgres_service import save_incident
        await save_incident(
            incident_id=incident_id,
            session_id=None,
            priority=priority,
            incident_type=incident_type,
            location=location or {},
            address="",
            recommended_assets=[{"type": a} for a in formatted_assets],
            critical_instructions=reasoning,
            reasoning=reasoning,
        )
        
        return IncidentResponse(
            incident_id=incident_id,
            status="analyzed",
            priority=priority,
            incident_type=incident_type,
            recommended_assets=formatted_assets,
            reasoning=reasoning,
            requires_approval=requires_approval,
            retrieved_docs=result.get("retrieved_docs", []),
        )
        
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        # Fallback: Use visual detection if available
        return IncidentResponse(
            incident_id=incident_id,
            status="processing",
            priority="P2" if image_category else "P3",
            incident_type=image_category.capitalize() if image_category else "Pending",
            recommended_assets=[],
            reasoning=f"Visual detection: {image_category or 'None'} | Audio: {audio_transcript or 'None'} | Workflow failed: {str(e)}",
            requires_approval=True,
            retrieved_docs=[],
        )


@router.post("/{incident_id}/approve")
async def approve_incident(
    request: Request,
    incident_id: str,
    decision: str = "approved",
    edited_priority: Optional[str] = None,
    edited_assets: Optional[list] = None,
    notes: Optional[str] = None,
):
    """
    HITL approval endpoint - dispatcher approves, edits, or rejects recommendation.
    
    Args:
        incident_id: The incident ID to approve
        decision: "approved", "edited", or "rejected"
        edited_priority: If decision is "edited", the new priority
        edited_assets: If decision is "edited", the new recommended assets
        notes: Optional notes from dispatcher
    """
    from datetime import datetime
    from src.services.postgres_service import (
        save_approval, update_incident_status, save_dispatch
    )
    
    logger.info(f"🚦 HITL Decision for {incident_id}: {decision}")
    
    # Save approval to history (PostgreSQL)
    await save_approval(
        incident_id=incident_id,
        decision=decision,
        approved_by="dispatcher",  # TODO: Get from auth
        original_priority=None,  # Would need to fetch from incident
        edited_priority=edited_priority,
        original_assets=None,
        edited_assets=edited_assets,
        notes=notes or "",
    )
    
    if decision == "rejected":
        # Update incident status
        await update_incident_status(incident_id, "rejected")
        
        return {
            "incident_id": incident_id,
            "decision": "rejected",
            "status": "closed",
            "message": "Incident rejected by dispatcher. No dispatch initiated.",
            "persisted": True,
        }
    
    # Update incident status to approved/dispatched
    new_status = "dispatched" if decision == "approved" else "edited_and_dispatched"
    await update_incident_status(incident_id, new_status)
    
    # Create dispatch record
    service_type = "Emergency_Response"
    if edited_assets:
        for asset in edited_assets:
            await save_dispatch(
                incident_id=incident_id,
                service_type=asset if isinstance(asset, str) else asset.get("type", "Unit"),
                service_name=asset if isinstance(asset, str) else asset.get("type", "Unit"),
                quantity=1 if isinstance(asset, str) else asset.get("quantity", 1),
                notes=f"HITL {decision}: {notes or 'No notes'}",
            )
    else:
        await save_dispatch(
            incident_id=incident_id,
            service_type=service_type,
            service_name="Default Response Team",
            quantity=1,
            notes=f"HITL {decision}: {notes or 'No notes'}",
        )
    
    # Build response
    dispatch_record = {
        "incident_id": incident_id,
        "decision": decision,
        "approved_at": datetime.utcnow().isoformat(),
        "approved_by": "dispatcher",
        "status": new_status,
    }
    
    if decision == "edited":
        dispatch_record["edited_priority"] = edited_priority
        dispatch_record["edited_assets"] = edited_assets
    
    return {
        "incident_id": incident_id,
        "decision": decision,
        "status": new_status,
        "message": "✅ Emergency services have been notified and are responding.",
        "dispatch_record": dispatch_record,
        "persisted": True,
    }


@router.get("/list")
async def list_incidents(
    limit: int = 50,
    offset: int = 0,
):
    """
    Get all incidents for dashboard display.
    
    Returns a list of incidents with their details, sorted by creation time.
    """
    from src.services.postgres_service import get_all_incidents
    
    incidents = await get_all_incidents(limit=limit, offset=offset)
    return {
        "incidents": incidents,
        "count": len(incidents),
        "limit": limit,
        "offset": offset,
    }


@router.get("/dispatches")
async def list_dispatches(
    limit: int = 50,
    offset: int = 0,
):
    """
    Get all dispatched services for dashboard display.
    
    Returns a list of dispatched services with their incident context.
    """
    from src.services.postgres_service import get_all_dispatches
    
    dispatches = await get_all_dispatches(limit=limit, offset=offset)
    return {
        "dispatches": dispatches,
        "count": len(dispatches),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get incident status and details."""
    from src.services.postgres_service import get_postgres_client
    import json
    
    db = await get_postgres_client()
    
    try:
        row = await db.fetchrow(
            "SELECT * FROM incidents WHERE incident_id = $1",
            incident_id
        )
        
        if not row:
            return {
                "incident_id": incident_id,
                "status": "not_found",
                "message": "Incident not found",
            }
        
        return {
            "incident_id": row["incident_id"],
            "priority": row["priority"],
            "incident_type": row["incident_type"],
            "location": json.loads(row["location"]) if row["location"] else None,
            "address": row["address"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    except Exception as e:
        logger.error(f"Failed to fetch incident: {e}")
        return {
            "incident_id": incident_id,
            "status": "error",
            "message": str(e),
        }

