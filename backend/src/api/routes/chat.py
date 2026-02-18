"""
Chat API - Multi-turn conversation with agent workflow integration
"""
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from src.services.redis_service import get_redis_client
from src.graph.orchestrator import Orchestrator

router = APIRouter()


# ============ SCHEMAS ============

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message text")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    session_id: Optional[str] = Field(None, description="Session UUID (auto-generated if not provided)")
    message: str = Field(..., description="User message")
    role: str = Field(default="dispatcher", description="User role: dispatcher, commander, or public")
    image_url: Optional[str] = None
    audio_url: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    session_id: str
    message_id: str
    ai_response: str
    incident_data: Optional[Dict[str, Any]] = None
    timestamp: str
    conversation_complete: bool = False


# ============ REDIS HELPERS ============

async def get_conversation_history(session_id: str) -> List[Dict]:
    """Load conversation history from Redis."""
    redis = await get_redis_client()
    key = f"session:{session_id}:messages"
    
    messages_json = await redis.get(key)
    if not messages_json:
        return []
    
    return json.loads(messages_json)


async def save_message(session_id: str, message: ChatMessage):
    """Save a message to Redis conversation history."""
    redis = await get_redis_client()
    key = f"session:{session_id}:messages"
    
    # Load existing
    history = await get_conversation_history(session_id)
    
    # Append new message
    history.append(message.model_dump())
    
    # Save with 24h TTL
    await redis.setex(key, 86400, json.dumps(history))


async def save_session_metadata(session_id: str, role: str):
    """Save session metadata."""
    redis = await get_redis_client()
    key = f"session:{session_id}:metadata"
    
    metadata = {
        "user_role": role,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
    }
    
    await redis.setex(key, 86400, json.dumps(metadata))


# ============ ENDPOINTS ============

@router.post("/message", response_model=ChatResponse)
async def send_message(request: Request, chat_request: ChatRequest):
    """
    Send a chat message and get AI response.
    
    Flow:
    1. Load conversation history from Redis
    2. Append user message
    3. Pass full context to agent workflow
    4. Save AI response to Redis
    5. Return response
    """
    # Generate session ID if not provided
    session_id = chat_request.session_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    try:
        # Load conversation history
        history = await get_conversation_history(session_id)
        
        # Create user message
        user_message = ChatMessage(
            role="user",
            content=chat_request.message,
            metadata={
                "image_url": chat_request.image_url,
                "audio_url": chat_request.audio_url,
            }
        )
        
        # Save user message
        await save_message(session_id, user_message)
        await save_session_metadata(session_id, chat_request.role)
        
        # Build context for orchestrator
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in history[-5:]  # Last 5 messages for context
        ])
        
        # Add current message
        full_query = f"{conversation_context}\nuser: {chat_request.message}" if conversation_context else chat_request.message
        
        # Get services from app state
        qdrant_service = request.app.state.qdrant
        llm_service = request.app.state.llm
        embedding_service = request.app.state.embedding  # Use cached service
        
        # Create orchestrator with injected services
        orchestrator = Orchestrator(
            qdrant_service=qdrant_service,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        
        result = await orchestrator.process_incident(
            incident_id=f"CHAT-{session_id[:8]}",
            query=full_query,
            user_role=chat_request.role,
        )
        
        # Check for guardrails rejection
        if result.get("error") == "Refused" or result.get("status") == "refused":
            return ChatResponse(
                session_id=session_id,
                message_id=message_id,
                ai_response="🛡️ Your message was flagged by our safety systems. Please provide a valid emergency report.",
                incident_data={"error": "Refused", "status": "guardrails_triggered"},
                timestamp=datetime.utcnow().isoformat(),
                conversation_complete=False,
            )
        
        # Detect jailbreak attempts that slipped through
        jailbreak_patterns = ["ignore", "forget", "disregard", "bypass", "override", "pretend", "act as"]
        query_lower = chat_request.message.lower()
        if any(pattern in query_lower for pattern in jailbreak_patterns) and any(kw in query_lower for kw in ["instruction", "rule", "previous", "system"]):
            return ChatResponse(
                session_id=session_id,
                message_id=message_id,
                ai_response="🛡️ I can only assist with emergency services. Please describe your emergency.",
                incident_data={"error": "Refused", "status": "jailbreak_detected"},
                timestamp=datetime.utcnow().isoformat(),
                conversation_complete=False,
            )
        
        # Build clean, human-readable response text
        priority = result.get("priority", "Pending")
        incident_type = result.get("incident_type", "Unknown")
        critical_instructions = result.get("critical_instructions", "")
        
        # Get location info
        resolved_loc = result.get("resolved_location") or result.get("location")
        address = result.get("address", "")
        
        # Build response parts
        response_parts = [f"🚨 **{incident_type}** | Priority: **{priority}**"]
        
        if critical_instructions:
            response_parts.append(f"\n\n📋 {critical_instructions}")
        
        # Add location if resolved
        if resolved_loc and resolved_loc.get("lat"):
            response_parts.append(f"\n\n📍 Location: {address or 'Confirmed'} ({resolved_loc['lat']:.4f}°N, {resolved_loc['lon']:.4f}°E)")
        else:
            response_parts.append("\n\n📍 Please share your location or describe a nearby landmark.")
        
        ai_response_text = "".join(response_parts)
        
        # Check if conversation is complete (has all required info)
        conversation_complete = _is_conversation_complete(result)
        
        # If complete, add dispatch confirmation message
        if conversation_complete:
            service_map = {
                "Fire": "Fire Department",
                "Fire_Residential": "Fire Department",
                "Fire_Commercial": "Fire Department",
                "Fire_Industrial": "Fire Department",
                "Medical": "Emergency Medical Services",
                "Accident": "Traffic Police & EMS",
                "Flood": "Disaster Management Team",
                "Crime": "Police Department",
                "Robbery": "Police Department",
                "Assault": "Police Department",
            }
            # Get the service name based on incident type
            service_name = None
            for key, value in service_map.items():
                if key.lower() in incident_type.lower():
                    service_name = value
                    break
            service_name = service_name or "Emergency Services"
            ai_response_text += f"\n\n✅ **Incident Dispatched!** I have notified the **{service_name}** and activated the recommended assets."
        
        # Create AI message
        ai_message = ChatMessage(
            role="assistant",
            content=ai_response_text,
            metadata={"incident_data": result}
        )
        
        # Save AI message
        await save_message(session_id, ai_message)
        
        # Check if conversation is complete (has all required info)
        conversation_complete = _is_conversation_complete(result)
        
        # If complete, save to Postgres
        if conversation_complete:
            await _save_to_postgres(session_id, history, result)
        
        return ChatResponse(
            session_id=session_id,
            message_id=message_id,
            ai_response=ai_response_text,
            incident_data=result,
            timestamp=datetime.utcnow().isoformat(),
            conversation_complete=conversation_complete,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/multimodal", response_model=ChatResponse)
async def send_multimodal_message(
    request: Request,
    session_id: Optional[str] = Form(default=None),
    message: str = Form(...),
    role: str = Form(default="public"),
    image: Optional[UploadFile] = File(default=None),
    audio: Optional[UploadFile] = File(default=None),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
):
    """
    Send a multimodal chat message with image, audio, or location.
    
    Flow:
    1. Process image via CLIP for visual detection
    2. Transcribe audio via Whisper
    3. Combine all context into message
    4. Pass to orchestrator
    5. Return AI response
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Generate session ID if not provided
    session_id = session_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    try:
        # Get services from app state
        qdrant_service = request.app.state.qdrant
        llm_service = request.app.state.llm
        embedding_service = request.app.state.embedding
        
        # Build combined message with multimodal context
        query_parts = []
        image_category = None
        image_embeddings = None
        audio_transcript = None
        location = None
        
        # Process image if provided
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
                    top_match = matches[0]
                    image_category = top_match.get("payload", {}).get("category", "unknown")
                    confidence = top_match.get("score", 0)
                    logger.info(f"🔍 Visual match: {image_category} (confidence: {confidence:.2f})")
                    query_parts.append(f"[VISUAL DETECTION: {image_category.upper()} incident detected from uploaded image]")
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
        
        # Process audio if provided
        if audio:
            try:
                from src.services.whisper_service import transcribe_audio
                audio_bytes = await audio.read()
                audio_transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.wav")
                if audio_transcript and not audio_transcript.startswith("["):
                    query_parts.append(f"[AUDIO TRANSCRIPT: {audio_transcript}]")
                    logger.info(f"🎤 Audio transcribed: {audio_transcript[:50]}...")
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}")
        
        # Add location context
        if lat and lon:
            location = {"lat": lat, "lon": lon}
            query_parts.append(f"[LOCATION: {lat}, {lon}]")
        
        # Add user message
        query_parts.append(message)
        
        full_query = "\n".join(query_parts)
        logger.info(f"📝 Combined query:\n{full_query}")
        
        # Load conversation history
        history = await get_conversation_history(session_id)
        
        # Create user message
        user_message = ChatMessage(
            role="user",
            content=full_query,
            metadata={
                "image_category": image_category,
                "has_audio": audio is not None,
                "location": location,
            }
        )
        
        # Save user message
        await save_message(session_id, user_message)
        await save_session_metadata(session_id, role)
        
        # Build context from history (handle different formats safely)
        context_parts = []
        for m in history[-5:]:
            if isinstance(m, dict):
                role = m.get('role', 'user')
                content = m.get('content', '')
                context_parts.append(f"{role}: {content}")
            elif isinstance(m, str):
                context_parts.append(m)
        context = "\n".join(context_parts)
        contextual_query = f"Conversation history:\n{context}\n\nCurrent message: {full_query}" if context else full_query
        
        # Initialize orchestrator
        orchestrator = Orchestrator(
            qdrant_service=qdrant_service,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        
        # Generate incident ID for this session
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        # Process through orchestrator
        result = await orchestrator.process_incident(
            incident_id=incident_id,
            query=contextual_query,
            text_input=full_query,
            channel="whatsapp_sim",
            user_role=role,
            location=location,
            image_embeddings=[image_embeddings] if image_embeddings else None,
        )
        
        # Apply visual override like in incidents.py
        priority = result.get("priority", "P3")
        incident_type = result.get("incident_type", "Unknown")
        
        # Visual detection OVERRIDES LLM
        visual_type_map = {
            "fire_disaster": "Fire",
            "urban_fire": "Fire",
            "wild_fire": "Fire",
            "water_disaster": "Flood",
            "human_damage": "Medical",
            "land_disaster": "Landslide",
            "land_slide": "Landslide",
            "earthquake": "Earthquake",
            "damaged_infrastructure": "Infrastructure",
        }
        
        if image_category and image_category.lower() in visual_type_map:
            incident_type = visual_type_map[image_category.lower()]
            logger.info(f"🔥 VISUAL OVERRIDE: Using {incident_type} from image")
            if incident_type in ["Fire", "Medical", "Earthquake"] and priority in ["P3", "P4"]:
                priority = "P2"
        
        # Format response text
        reasoning = result.get("reasoning", result.get("critical_instructions", ""))
        assets = result.get("recommended_assets", [])
        
        # Add visual context to response
        if image_category:
            reasoning = f"[VISUAL: {image_category.upper()} detected] {reasoning}"
        
        # Handle assets that might be dicts or strings
        if assets:
            asset_strings = []
            for a in assets[:3]:
                if isinstance(a, dict):
                    asset_strings.append(a.get("type", str(a)))
                else:
                    asset_strings.append(str(a))
            assets_text = ", ".join(asset_strings)
        else:
            assets_text = "Pending dispatch"
        
        ai_response_text = f"""**{incident_type} Emergency** (Priority: {priority})

{reasoning}

🚑 **Recommended Assets:** {assets_text}

⚠️ This incident requires dispatcher approval before dispatch."""
        
        # Create AI message
        ai_message = ChatMessage(
            role="assistant",
            content=ai_response_text,
            metadata={
                "incident_id": incident_id,
                "priority": priority,
                "incident_type": incident_type,
                "image_category": image_category,
            }
        )
        
        # Save AI message
        await save_message(session_id, ai_message)
        
        # Check if we have enough info to save incident
        conversation_complete = priority in ["P1", "P2"] or len(history) > 2
        
        # Save to PostgreSQL if complete
        if conversation_complete:
            from src.services.postgres_service import save_incident
            await save_incident(
                incident_id=incident_id,
                session_id=session_id,
                priority=priority,
                incident_type=incident_type,
                location=location or {},
                address="",
                recommended_assets=[{"type": a} for a in assets],
                critical_instructions=reasoning,
                reasoning=reasoning,
            )
        
        return ChatResponse(
            session_id=session_id,
            message_id=message_id,
            ai_response=ai_response_text,
            incident_data={
                "incident_id": incident_id,
                "priority": priority,
                "incident_type": incident_type,
                "image_category": image_category,
            },
            timestamp=datetime.utcnow().isoformat(),
            conversation_complete=conversation_complete,
        )
        
    except Exception as e:
        logger.error(f"Multimodal chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    history = await get_conversation_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session."""
    redis = await get_redis_client()
    await redis.delete(f"session:{session_id}:messages")
    await redis.delete(f"session:{session_id}:metadata")
    return {"status": "cleared", "session_id": session_id}


# ============ HELPERS ============

def _is_conversation_complete(result: Dict) -> bool:
    """Check if we have all required info to save incident."""
    # Must have priority, type, and a resolved location (lat/lon)
    priority = result.get("priority")
    incident_type = result.get("incident_type")
    location = result.get("resolved_location") or result.get("location")
    
    # Check if location has lat/lon
    has_location = isinstance(location, dict) and location.get("lat") and location.get("lon")
    
    # Check if priority is valid (not Pending)
    has_priority = priority and priority != "Pending"
    
    # Check if incident_type is valid (not Unknown)
    has_type = incident_type and incident_type not in ["Unknown", "Pending", "Multimodal_Pending", "ADMIN_InformationRequest"]
    
    return bool(has_location and has_priority and has_type)


async def _save_to_postgres(session_id: str, history: List[Dict], result: Dict):
    """Save complete incident and dispatched services to Postgres."""
    from src.services.postgres_service import save_incident, save_dispatch, update_incident_status
    
    incident_id = result.get("incident_id")
    location = result.get("resolved_location") or result.get("location") or {}
    
    # Save the incident
    await save_incident(
        incident_id=incident_id,
        session_id=session_id,
        priority=result.get("priority", "P3"),
        incident_type=result.get("incident_type", "Unknown"),
        location=location,
        address=result.get("address", ""),
        conversation_history=history,
        recommended_assets=result.get("recommended_assets", []),
        critical_instructions=result.get("critical_instructions", ""),
        reasoning=result.get("reasoning", ""),
        quality_score=result.get("quality_score", 0.0),
    )
    
    # Update status to dispatched - REMOVED to allow dispatcher review
    # await update_incident_status(incident_id, "dispatched")
    
    # Save dispatched services based on recommended_assets
    recommended_assets = result.get("recommended_assets", [])
    incident_type = result.get("incident_type", "")
    
    # Map incident type to service name
    service_map = {
        "Fire": ("Fire Department", "Fire_Truck"),
        "Fire_Residential": ("Fire Department", "Fire_Truck"),
        "Fire_Commercial": ("Fire Department", "Fire_Truck"),
        "Medical": ("Emergency Medical Services", "Ambulance"),
        "Medical_Trauma": ("Emergency Medical Services", "ALS_Ambulance"),
        "Medical_Cardiac": ("Emergency Medical Services", "ALS_Ambulance"),
        "Accident": ("Traffic Police & EMS", "Police_Patrol"),
        "Accident_Vehicle": ("Traffic Police & EMS", "Police_Patrol"),
        "Flood": ("Disaster Management", "NDRF_Team"),
        "Crime": ("Police Department", "Police_Patrol"),
        "HazMat": ("HazMat Response", "HazMat_Team"),
    }
    
    # Find matching service
    service_name = "Emergency Services"
    service_type = "General"
    
    for key, (name, stype) in service_map.items():
        if key.lower() in incident_type.lower():
            service_name = name
            service_type = stype
            break
    
    # If we have specific recommended assets, save each one
    if recommended_assets:
        for asset in recommended_assets:
            if isinstance(asset, dict):
                await save_dispatch(
                    incident_id=incident_id,
                    service_type=asset.get("type", service_type),
                    service_name=service_name,
                    quantity=asset.get("quantity", 1),
                )
            elif isinstance(asset, str):
                await save_dispatch(
                    incident_id=incident_id,
                    service_type=asset,
                    service_name=service_name,
                    quantity=1,
                )
    else:
        # Save a default dispatch based on incident type
        await save_dispatch(
            incident_id=incident_id,
            service_type=service_type,
            service_name=service_name,
            quantity=1,
        )

