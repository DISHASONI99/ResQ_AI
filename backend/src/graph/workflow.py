"""
LangGraph Workflow - Agent orchestration graph

Defines the agent workflow using LangGraph:
- Supervisor → Triage/Geo/Vision
- Triage → Protocol → Reflector
- Reflector → HITL or Loop Back
"""
import logging
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END

from src.graph.state import IncidentState
from src.agents.schemas import AgentInput, ConfidenceBreakdown
from src.config import settings

logger = logging.getLogger(__name__)


def build_agent_input(state: IncidentState) -> AgentInput:
    """Convert workflow state to AgentInput for agents."""
    return AgentInput(
        incident_id=state.get("incident_id", ""),
        query=state.get("query", ""),
        channel=state.get("channel", "web"),
        user_role=state.get("user_role", "dispatcher"),
        text_input=state.get("text_input", ""),
        audio_transcript=state.get("audio_transcript"),
        image_embeddings=state.get("image_embeddings"),
        location=state.get("location"),
        retrieved_docs=state.get("retrieved_docs", []),
        retrieved_images=state.get("retrieved_images", []),
        retrieved_sops=state.get("retrieved_sops", []),
        retrieved_landmarks=state.get("retrieved_landmarks", []),
        agent_history=state.get("agent_history", []),
        previous_outputs=_build_previous_outputs(state),
    )


def _build_previous_outputs(state: IncidentState) -> Dict[str, Any]:
    """Build previous_outputs dict from state for agent context."""
    outputs = {}
    
    # Supervisor outputs
    if state.get("intent"):
        outputs["supervisor"] = {
            "intent": state.get("intent"),
            "initial_assessment": state.get("initial_assessment"),
        }
    
    # Triage outputs
    if state.get("priority"):
        outputs["triage"] = {
            "priority": state.get("priority"),
            "incident_type": state.get("incident_type"),
            "recommended_assets": state.get("recommended_assets", []),
        }
    
    # Geo outputs
    if state.get("resolved_location"):
        outputs["geo"] = {
            "resolved_location": state.get("resolved_location"),
            "address": state.get("address"),
            "nearby_landmarks": state.get("nearby_landmarks", []),
        }
    
    # Protocol outputs
    if state.get("recommended_sops"):
        outputs["protocol"] = {
            "recommended_sops": state.get("recommended_sops"),
            "critical_instructions": state.get("critical_instructions"),
        }
    
    # Vision outputs
    if state.get("visual_analysis"):
        outputs["vision"] = {
            "visual_analysis": state.get("visual_analysis"),
            "visual_confirmation": state.get("visual_confirmation"),
        }
    
    return outputs


class AgentWorkflow:
    """
    LangGraph workflow for emergency response agents.
    
    Flow:
    Supervisor → (Triage | Geo | Vision) → Protocol → Reflector → HITL
    
    With loop-back capability if Reflector detects gaps.
    """
    
    def __init__(
        self,
        qdrant_service,
        embedding_service,
        llm_service,
        config: dict,
    ):
        self.qdrant = qdrant_service
        self.embedding = embedding_service
        self.llm = llm_service
        self.config = config
        
        # Initialize agents lazily
        self._agents = {}
        self._graph = None
    
    def _get_agent(self, name: str):
        """Lazy initialization of agents."""
        if name not in self._agents:
            if name == "supervisor":
                from src.agents.supervisor import SupervisorAgent
                self._agents[name] = SupervisorAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            elif name == "triage":
                from src.agents.triage import TriageAgent
                self._agents[name] = TriageAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            elif name == "geo":
                from src.agents.geo import GeoAgent
                self._agents[name] = GeoAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            elif name == "protocol":
                from src.agents.protocol import ProtocolAgent
                self._agents[name] = ProtocolAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            elif name == "vision":
                from src.agents.vision import VisionAgent
                self._agents[name] = VisionAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            elif name == "reflector":
                from src.agents.reflector import ReflectorAgent
                self._agents[name] = ReflectorAgent(
                    self.qdrant, self.embedding, self.llm, self.config
                )
            else:
                raise ValueError(f"Unknown agent: {name}")
        return self._agents[name]
    
    async def _run_supervisor(self, state: IncidentState) -> IncidentState:
        """Run supervisor agent node."""
        logger.info("🎯 Running Supervisor Agent")
        agent = self._get_agent("supervisor")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        # Update state
        result = output.result
        state["intent"] = result.get("intent", "unclear")
        state["initial_assessment"] = result.get("initial_assessment", "")
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["supervisor"]
        state["requires_human_approval"] = output.requires_human_approval
        state["requires_more_info"] = output.requires_more_info
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        if output.ambiguities:
            state["ambiguities"] = [a.model_dump() for a in output.ambiguities]
        
        return state
    
    async def _run_triage(self, state: IncidentState) -> IncidentState:
        """Run triage agent node."""
        logger.info("🚨 Running Triage Agent")
        agent = self._get_agent("triage")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        result = output.result
        state["priority"] = result.get("priority", "P3")
        state["incident_type"] = result.get("incident_type", "Unknown")
        state["recommended_assets"] = result.get("recommended_assets", [])
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["triage"]
        state["requires_human_approval"] = output.requires_human_approval
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        # Add grounded claims
        if output.grounded_claims:
            existing = state.get("grounded_claims", [])
            state["grounded_claims"] = existing + [c.model_dump() for c in output.grounded_claims]
        
        return state
    
    async def _run_geo(self, state: IncidentState) -> IncidentState:
        """Run geo agent node."""
        logger.info("📍 Running Geo Agent")
        agent = self._get_agent("geo")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        result = output.result
        state["resolved_location"] = result.get("resolved_location")
        state["address"] = result.get("address")
        state["nearby_landmarks"] = result.get("nearby_landmarks", [])
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["geo"]
        state["requires_more_info"] = output.requires_more_info
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        if output.ambiguities:
            existing = state.get("ambiguities", [])
            state["ambiguities"] = existing + [a.model_dump() for a in output.ambiguities]
        
        return state
    
    async def _run_protocol(self, state: IncidentState) -> IncidentState:
        """Run protocol agent node."""
        logger.info("📋 Running Protocol Agent")
        agent = self._get_agent("protocol")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        result = output.result
        state["recommended_sops"] = result.get("recommended_sops", [])
        state["critical_instructions"] = result.get("critical_instructions", "")
        state["contraindications"] = result.get("contraindications")
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["protocol"]
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        if output.grounded_claims:
            existing = state.get("grounded_claims", [])
            state["grounded_claims"] = existing + [c.model_dump() for c in output.grounded_claims]
        
        return state
    
    async def _run_vision(self, state: IncidentState) -> IncidentState:
        """Run vision agent node."""
        logger.info("👁️ Running Vision Agent")
        agent = self._get_agent("vision")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        result = output.result
        state["visual_analysis"] = result.get("image_analysis")
        state["visual_confirmation"] = result.get("visual_confirmation", False)
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["vision"]
        state["requires_more_info"] = output.requires_more_info
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        return state
    
    async def _run_reflector(self, state: IncidentState) -> IncidentState:
        """Run reflector agent node."""
        logger.info("🔍 Running Reflector Agent")
        agent = self._get_agent("reflector")
        agent_input = build_agent_input(state)
        
        output = await agent.process(agent_input)
        
        result = output.result
        state["quality_score"] = result.get("quality_score", 0.7)
        state["gaps_detected"] = result.get("gaps_detected", [])
        state["grounding_issues"] = result.get("grounding_issues", [])
        state["reflection_complete"] = True
        state["next_agent"] = output.next_agent
        state["agent_history"] = state.get("agent_history", []) + ["reflector"]
        state["requires_human_approval"] = output.requires_human_approval
        state["requires_more_info"] = output.requires_more_info
        state["loop_back_to"] = output.next_agent if output.requires_more_info else None
        state["total_processing_time_ms"] = state.get("total_processing_time_ms", 0) + output.processing_time_ms
        state["total_tokens_consumed"] = state.get("total_tokens_consumed", 0) + output.tokens_consumed
        
        return state
    
    def _route_after_supervisor(self, state: IncidentState) -> str:
        """Route based on supervisor's intent classification."""
        intent = state.get("intent", "unclear")
        next_agent = state.get("next_agent")
        
        # If supervisor explicitly says unclear, go to HITL
        if intent == "unclear" or state.get("requires_human_approval"):
            return "hitl"
        
        # Route based on intent
        if intent == "location_unclear":
            return "geo"
        elif intent == "visual_needed":
            return "vision"
        else:
            # medical, fire, accident, crime → triage
            return "triage"
    
    def _route_after_geo(self, state: IncidentState) -> str:
        """Route after geo resolution."""
        if state.get("requires_more_info"):
            return "hitl"  # Need human to clarify location
        return "triage"
    
    def _route_after_vision(self, state: IncidentState) -> str:
        """Route after vision analysis."""
        if state.get("requires_more_info"):
            return "hitl"
        return "triage"
    
    def _route_after_triage(self, state: IncidentState) -> str:
        """Route after triage."""
        return "protocol"
    
    def _route_after_protocol(self, state: IncidentState) -> str:
        """Route after protocol."""
        return "reflector"
    
    def _route_after_reflector(self, state: IncidentState) -> str:
        """Route based on reflector's quality assessment."""
        quality_score = state.get("quality_score", 0.7)
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)
        
        # Prevent infinite loops
        if iteration_count >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached, proceeding to HITL")
            return "hitl"
        
        # High quality → HITL for approval
        if quality_score >= 0.7:
            return "hitl"
        
        # Low quality → loop back
        loop_back_to = state.get("loop_back_to")
        if loop_back_to and loop_back_to in ["supervisor", "triage", "geo"]:
            state["iteration_count"] = iteration_count + 1
            return loop_back_to
        
        # Default to HITL
        return "hitl"
    
    def _hitl_node(self, state: IncidentState) -> IncidentState:
        """
        Human-in-the-loop checkpoint.
        
        Marks the workflow as requiring human approval.
        The actual approval happens outside this graph.
        """
        logger.info("⏸️ HITL Checkpoint - Awaiting Human Approval")
        
        # Build final recommendation
        state["final_recommendation"] = {
            "incident_id": state.get("incident_id"),
            "priority": state.get("priority", "P3"),
            "incident_type": state.get("incident_type", "Unknown"),
            "recommended_assets": state.get("recommended_assets", []),
            "location": state.get("resolved_location"),
            "address": state.get("address"),
            "critical_instructions": state.get("critical_instructions", ""),
            "recommended_sops": state.get("recommended_sops", []),
            "quality_score": state.get("quality_score", 0.7),
            "gaps_detected": state.get("gaps_detected", []),
            "grounded_claims_count": len(state.get("grounded_claims", [])),
        }
        
        state["processing_complete"] = True
        state["requires_human_approval"] = True
        
        return state
    
    def build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        if self._graph is not None:
            return self._graph
        
        # Create graph
        workflow = StateGraph(IncidentState)
        
        # Add nodes
        workflow.add_node("supervisor", self._run_supervisor)
        workflow.add_node("triage", self._run_triage)
        workflow.add_node("geo", self._run_geo)
        workflow.add_node("protocol", self._run_protocol)
        workflow.add_node("vision", self._run_vision)
        workflow.add_node("reflector", self._run_reflector)
        workflow.add_node("hitl", self._hitl_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "triage": "triage",
                "geo": "geo",
                "vision": "vision",
                "hitl": "hitl",
            }
        )
        
        workflow.add_conditional_edges(
            "geo",
            self._route_after_geo,
            {
                "triage": "triage",
                "hitl": "hitl",
            }
        )
        
        workflow.add_conditional_edges(
            "vision",
            self._route_after_vision,
            {
                "triage": "triage",
                "hitl": "hitl",
            }
        )
        
        workflow.add_edge("triage", "protocol")
        workflow.add_edge("protocol", "reflector")
        
        workflow.add_conditional_edges(
            "reflector",
            self._route_after_reflector,
            {
                "supervisor": "supervisor",
                "triage": "triage",
                "geo": "geo",
                "hitl": "hitl",
            }
        )
        
        # HITL is the end
        workflow.add_edge("hitl", END)
        
        self._graph = workflow.compile()
        return self._graph
    
    async def run(self, initial_state: IncidentState) -> IncidentState:
        """Execute the workflow with given initial state."""
        graph = self.build_graph()
        
        logger.info(f"🚀 Starting workflow for incident: {initial_state.get('incident_id')}")
        
        # Run the graph
        final_state = await graph.ainvoke(initial_state)
        
        logger.info(f"✅ Workflow complete. Quality: {final_state.get('quality_score', 'N/A')}")
        
        return final_state
