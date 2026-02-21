"""
Graph State - Shared state for LangGraph workflow

This TypedDict defines the state that flows between all agents.
"""
from typing import Any, Dict, List, Literal, Optional, TypedDict

from src.agents.schemas import (
    ConfidenceBreakdown,
    GroundedClaim,
    AmbiguityFlag,
)


class IncidentState(TypedDict, total=False):
    """
    Shared state that flows through the LangGraph workflow.
    
    Each agent reads from and writes to this state.
    Using total=False makes all fields optional.
    """
    
    # ============ INPUT ============
    incident_id: str
    query: str
    channel: Literal["web", "whatsapp_sim"]
    user_role: Literal["dispatcher", "commander", "public"]
    
    # Multimodal inputs
    text_input: str
    audio_transcript: Optional[str]
    image_embeddings: Optional[List[List[float]]]
    location: Optional[Dict[str, float]]  # {lat, lon}
    
    # Retrieved context (from Qdrant)
    retrieved_docs: List[Dict[str, Any]]
    retrieved_images: List[Dict[str, Any]]
    retrieved_sops: List[Dict[str, Any]]
    retrieved_landmarks: List[Dict[str, Any]]
    
    # ============ WORKFLOW STATE ============
    current_agent: str
    agent_history: List[str]
    iteration_count: int
    max_iterations: int
    
    # ============ AGENT OUTPUTS ============
    # Supervisor
    intent: str
    initial_assessment: str
    
    # Triage
    priority: Literal["P1", "P2", "P3", "P4", "P5"]
    incident_type: str
    recommended_assets: List[Dict[str, Any]]
    
    # Geo
    resolved_location: Optional[Dict[str, Any]]
    address: Optional[str]
    nearby_landmarks: List[str]
    
    # Protocol
    recommended_sops: List[Dict[str, Any]]
    critical_instructions: str
    contraindications: Optional[str]
    
    # Vision
    visual_analysis: Optional[Dict[str, Any]]
    visual_confirmation: bool
    
    # Reflector
    quality_score: float
    gaps_detected: List[str]
    grounding_issues: List[str]
    reflection_complete: bool
    
    # ============ GROUNDING & CONFIDENCE ============
    grounded_claims: List[Dict[str, Any]]  # Serialized GroundedClaim
    confidence: Dict[str, float]  # Serialized ConfidenceBreakdown
    ambiguities: List[Dict[str, Any]]  # Serialized AmbiguityFlag
    
    # ============ WORKFLOW CONTROL ============
    next_agent: Optional[str]
    requires_human_approval: bool
    requires_more_info: bool
    loop_back_to: Optional[str]
    
    # ============ FINAL OUTPUT ============
    final_recommendation: Optional[Dict[str, Any]]
    processing_complete: bool
    
    # ============ AUDIT ============
    total_processing_time_ms: int
    total_tokens_consumed: int
    errors: List[str]


def create_initial_state(
    incident_id: str,
    query: str,
    text_input: str,
    channel: str = "web",
    user_role: str = "dispatcher",
    location: Optional[Dict[str, float]] = None,
    audio_transcript: Optional[str] = None,
    image_embeddings: Optional[List[List[float]]] = None,
) -> IncidentState:
    """
    Factory function to create initial state for a new incident.
    """
    return IncidentState(
        # Input
        incident_id=incident_id,
        query=query,
        channel=channel,
        user_role=user_role,
        text_input=text_input,
        audio_transcript=audio_transcript,
        image_embeddings=image_embeddings,
        location=location,
        
        # Retrieved (empty initially)
        retrieved_docs=[],
        retrieved_images=[],
        retrieved_sops=[],
        retrieved_landmarks=[],
        
        # Workflow
        current_agent="supervisor",
        agent_history=[],
        iteration_count=0,
        max_iterations=5,
        
        # Outputs (empty initially)
        priority="P3",
        incident_type="Unknown",
        recommended_assets=[],
        nearby_landmarks=[],
        recommended_sops=[],
        grounded_claims=[],
        ambiguities=[],
        gaps_detected=[],
        grounding_issues=[],
        errors=[],
        
        # Control
        requires_human_approval=False,
        requires_more_info=False,
        processing_complete=False,
        reflection_complete=False,
        
        # Audit
        total_processing_time_ms=0,
        total_tokens_consumed=0,
    )
