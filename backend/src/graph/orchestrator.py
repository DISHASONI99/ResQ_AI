"""
Orchestrator - Entry point for agent workflow

Handles:
- Test mode: Single large model call (bypasses multi-agent)
- Prod mode: Full LangGraph multi-agent workflow
- Retrieval augmentation before workflow
- Idempotency via incident_id tracking
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from src.config import settings
from src.graph.state import IncidentState, create_initial_state
from src.graph.workflow import AgentWorkflow

logger = logging.getLogger(__name__)


# ============ TEST MODE PROMPT ============

TEST_MODE_SYSTEM_PROMPT = """You are an Emergency Response AI Assistant.

Given an emergency report, provide a complete assessment including:
1. Priority (P1-P5)
2. Incident type classification
3. Recommended response assets
4. Critical instructions for dispatcher

OUTPUT FORMAT (JSON):
{
  "priority": "P1|P2|P3|P4|P5",
  "incident_type": "Category_Subcategory",
  "recommended_assets": [{"type": "ALS_Ambulance", "quantity": 1}],
  "critical_instructions": "Immediate actions for dispatcher",
  "reasoning": "Why this classification",
  "confidence": 0.0-1.0
}

PRIORITY LEVELS:
- P1 (CRITICAL): Immediate life threat
- P2 (URGENT): Serious but stable
- P3 (MODERATE): Non-life-threatening
- P4 (LOW): Scheduled response okay
- P5 (ADMIN): Information only

Be decisive and clear. Respond with valid JSON only."""


class Orchestrator:
    """
    Main entry point for the agentic system.
    
    Modes:
    - "test": Single LLM call with unified prompt (fast, for development)
    - "prod": Full multi-agent LangGraph workflow (production)
    
    Features:
    - Automatic retrieval augmentation
    - Idempotency tracking via incident_id
    - Graceful error handling
    """
    
    def __init__(
        self,
        qdrant_service,
        embedding_service,
        llm_service,
        config: Optional[dict] = None,
    ):
        """
        Initialize orchestrator with injected services.
        
        Args:
            qdrant_service: QdrantService for vector retrieval
            embedding_service: EmbeddingService for embeddings
            llm_service: PortkeyLLMService for LLM calls
            config: Optional config override
        """
        self.qdrant = qdrant_service
        self.embedding = embedding_service
        self.llm = llm_service
        self.config = config or {}
        
        # Mode from settings
        self.mode = getattr(settings, 'AGENT_MODE', 'prod')
        
        # Workflow instance (lazy init)
        self._workflow = None
        
        # Idempotency tracking (in-memory for now, use Redis in production)
        self._processed_incidents: Dict[str, Dict] = {}
        
        logger.info(f"🎛️ Orchestrator initialized in '{self.mode}' mode")
    
    @property
    def workflow(self) -> AgentWorkflow:
        """Lazy initialization of workflow."""
        if self._workflow is None:
            self._workflow = AgentWorkflow(
                qdrant_service=self.qdrant,
                embedding_service=self.embedding,
                llm_service=self.llm,
                config=self.config,
            )
        return self._workflow
    
    async def process_incident(
        self,
        incident_id: str,
        query: str,
        text_input: Optional[str] = None,
        channel: str = "web",
        user_role: str = "dispatcher",
        location: Optional[Dict[str, float]] = None,
        audio_transcript: Optional[str] = None,
        image_embeddings: Optional[list] = None,
        image_url: Optional[str] = None,
        audio_url: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> Dict[str, Any]:
        """
        Main entry point for processing an incident.
        
        Args:
            incident_id: Unique identifier for idempotency
            query: The emergency report text
            text_input: Optional additional text context
            channel: "web" or "whatsapp_sim"
            user_role: "dispatcher", "commander", or "public"
            location: Optional {lat, lon} dict
            audio_transcript: Optional transcribed audio
            image_embeddings: Optional CLIP embeddings
            force_reprocess: Skip idempotency check
        
        Returns:
            Final recommendation dict with priority, assets, instructions, etc.
        """
        start_time = time.time()
        
        # ============ IDEMPOTENCY CHECK ============
        if not force_reprocess and incident_id in self._processed_incidents:
            logger.info(f"⚡ Returning cached result for {incident_id}")
            return self._processed_incidents[incident_id]
        
        logger.info(f"📥 Processing incident {incident_id} in '{self.mode}' mode")
        
        try:
            # ============ RETRIEVAL AUGMENTATION ============
            retrieval_context = await self._retrieve_context(
                query=query,
                location=location,
                image_embeddings=image_embeddings,
            )
            
            # ============ MODE ROUTING ============
            if self.mode == "test":
                result = await self._process_test_mode(
                    incident_id=incident_id,
                    query=query,
                    retrieval_context=retrieval_context,
                )
            else:
                result = await self._process_prod_mode(
                    incident_id=incident_id,
                    query=query,
                    text_input=text_input or query,
                    channel=channel,
                    user_role=user_role,
                    location=location,
                    audio_transcript=audio_transcript,
                    image_embeddings=image_embeddings,
                    retrieval_context=retrieval_context,
                )
            
            # Add processing metadata
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            result["mode"] = self.mode
            
            # ============ IDEMPOTENCY STORE ============
            self._processed_incidents[incident_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Orchestrator error: {e}")
            return self._error_response(incident_id, str(e), start_time)
    
    async def _retrieve_context(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        image_embeddings: Optional[list] = None,
    ) -> Dict[str, list]:
        """
        Retrieve relevant context from Qdrant collections.
        """
        context = {
            "docs": [],
            "sops": [],
            "landmarks": [],
            "images": [],
        }
        
        try:
            # Embed query (sync function - no await)
            # embed_text returns List[List[float]], we need List[float]
            query_embedding = self.embedding.embed_text(query)[0]
            
            # Search incident memory (async - needs await)
            try:
                context["docs"] = await self.qdrant.hybrid_search(
                    collection="incident_memory",
                    dense_vector=query_embedding,
                    top_k=5,
                )
            except Exception as e:
                logger.warning(f"⚠️ Incident memory search failed: {e}")
            
            # Search SOPs
            try:
                context["sops"] = await self.qdrant.hybrid_search(
                    collection="protocols_sops",
                    dense_vector=query_embedding,
                    top_k=5,
                )
            except Exception as e:
                logger.warning(f"⚠️ SOP search failed: {e}")
            
            # Search landmarks if location unclear
            if location is None:
                try:
                    context["landmarks"] = await self.qdrant.hybrid_search(
                        collection="landmark_index",
                        dense_vector=query_embedding,
                        top_k=5,
                    )
                    if context["landmarks"]:
                        logger.info(f"📍 Found {len(context['landmarks'])} landmarks")
                except Exception as e:
                    logger.warning(f"⚠️ Landmark search failed: {e}")
            
            # Search visual evidence if images provided
            if image_embeddings:
                try:
                    context["images"] = await self.qdrant.hybrid_search(
                        collection="visual_evidence",
                        dense_vector=image_embeddings[0],
                        top_k=5,
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Visual search failed: {e}")
                
        except Exception as e:
            logger.warning(f"⚠️ Retrieval error: {e}")
        
        return context
    
    async def _process_test_mode(
        self,
        incident_id: str,
        query: str,
        retrieval_context: Dict[str, list],
    ) -> Dict[str, Any]:
        """
        Test mode: Single LLM call with large model.
        
        Uses PORTKEY_CONFIG_ID which should have 120B+ models.
        """
        logger.info("🧪 Test mode: Single LLM call")
        
        # Format context for prompt
        context_str = self._format_context_for_prompt(retrieval_context)
        
        user_prompt = f"""EMERGENCY REPORT:
{query}

RETRIEVED CONTEXT:
{context_str}

Provide a complete assessment with priority, assets, and instructions."""
        
        try:
            # Use main config (should have large model)
            response = await self.llm.generate(
                user_prompt=user_prompt,
                system_prompt=TEST_MODE_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            
            result = json.loads(response["content"])
            
            return {
                "incident_id": incident_id,
                "status": "test_complete",
                "priority": result.get("priority", "P3"),
                "incident_type": result.get("incident_type", "Unknown"),
                "recommended_assets": result.get("recommended_assets", []),
                "critical_instructions": result.get("critical_instructions", ""),
                "reasoning": result.get("reasoning", ""),
                "confidence": result.get("confidence", 0.7),
                "requires_human_approval": result.get("priority") in ["P1", "P2"],
                "tokens_consumed": response.get("usage", {}).get("total_tokens", 0),
                "model_used": response.get("model", "unknown"),
            }
            
        except Exception as e:
            logger.error(f"Test mode error: {e}")
            return self._error_response(incident_id, str(e), time.time())
    
    async def _process_prod_mode(
        self,
        incident_id: str,
        query: str,
        text_input: str,
        channel: str,
        user_role: str,
        location: Optional[Dict[str, float]],
        audio_transcript: Optional[str],
        image_embeddings: Optional[list],
        retrieval_context: Dict[str, list],
    ) -> Dict[str, Any]:
        """
        Prod mode: Full multi-agent LangGraph workflow.
        """
        logger.info("🚀 Prod mode: Multi-agent workflow")
        
        # Create initial state
        initial_state = create_initial_state(
            incident_id=incident_id,
            query=query,
            text_input=text_input,
            channel=channel,
            user_role=user_role,
            location=location,
            audio_transcript=audio_transcript,
            image_embeddings=image_embeddings,
        )
        
        # Add retrieved context
        initial_state["retrieved_docs"] = retrieval_context.get("docs", [])
        initial_state["retrieved_sops"] = retrieval_context.get("sops", [])
        initial_state["retrieved_landmarks"] = retrieval_context.get("landmarks", [])
        initial_state["retrieved_images"] = retrieval_context.get("images", [])
        
        # Run workflow
        final_state = await self.workflow.run(initial_state)
        
        # Extract result
        return {
            "incident_id": incident_id,
            "status": "workflow_complete",
            "priority": final_state.get("priority", "P3"),
            "incident_type": final_state.get("incident_type", "Unknown"),
            "recommended_assets": final_state.get("recommended_assets", []),
            "location": final_state.get("resolved_location"),
            "address": final_state.get("address"),
            "critical_instructions": final_state.get("critical_instructions", ""),
            "recommended_sops": final_state.get("recommended_sops", []),
            "quality_score": final_state.get("quality_score", 0.7),
            "gaps_detected": final_state.get("gaps_detected", []),
            "grounded_claims_count": len(final_state.get("grounded_claims", [])),
            "agent_history": final_state.get("agent_history", []),
            "requires_human_approval": final_state.get("requires_human_approval", True),
            "tokens_consumed": final_state.get("total_tokens_consumed", 0),
            "final_recommendation": final_state.get("final_recommendation"),
        }
    
    def _format_context_for_prompt(self, context: Dict[str, list]) -> str:
        """Format retrieved context for LLM prompt."""
        parts = []
        
        if context.get("sops"):
            sop_text = "\n".join([
                f"- {sop.get('content', sop.get('payload', {}).get('content', ''))[:200]}..."
                for sop in context["sops"][:3]
            ])
            parts.append(f"RELEVANT SOPs:\n{sop_text}")
        
        if context.get("docs"):
            docs_text = "\n".join([
                f"- {doc.get('content', doc.get('payload', {}).get('content', ''))[:200]}..."
                for doc in context["docs"][:3]
            ])
            parts.append(f"SIMILAR INCIDENTS:\n{docs_text}")
        
        return "\n\n".join(parts) if parts else "No relevant context found."
    
    def _error_response(self, incident_id: str, error: str, start_time: float) -> Dict[str, Any]:
        """Generate error response."""
        return {
            "incident_id": incident_id,
            "status": "error",
            "error": error,
            "priority": "P2",  # Conservative default
            "incident_type": "Unknown_RequiresReview",
            "recommended_assets": [{"type": "ALS_Ambulance", "quantity": 1}],
            "critical_instructions": "Escalate to human dispatcher immediately.",
            "requires_human_approval": True,
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }
    
    def clear_cache(self, incident_id: Optional[str] = None):
        """Clear idempotency cache."""
        if incident_id:
            self._processed_incidents.pop(incident_id, None)
        else:
            self._processed_incidents.clear()
        logger.info(f"🗑️ Cache cleared: {incident_id or 'all'}")
