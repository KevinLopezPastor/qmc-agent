
"""
QMC Agent - Graph Definition (V2.1)
Defines the Multi-Agent Workflow using LangGraph.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import QMCState, create_initial_state

# Import V2 Nodes (The "Agents")
from src.nodes.login_node_sync import login_node_sync
from src.nodes.extractor import extractor_node
from src.nodes.analyst_llm import analyst_llm_node
from src.nodes.reporter import reporter_node

# ============ Wrappers (Async/Sync Adapters) ============
# LangGraph prefers async nodes or compatible signatures.
# Our V2 nodes have mixed signatures, so we wrap them for consistency.

def login_agent(state: QMCState) -> dict:
    """Wrapper for Login Node."""
    return login_node_sync(state)

def extractor_agent(state: QMCState) -> dict:
    """Wrapper for Extractor Node."""
    return extractor_node(state)

async def analyst_agent(state: QMCState) -> dict:
    """Wrapper for Analyst Node (Already Async)."""
    return await analyst_llm_node(state)

def reporter_agent(state: QMCState) -> dict:
    """Wrapper for Reporter Node."""
    return reporter_node(state)

def error_agent(state: QMCState) -> dict:
    """Handle error state."""
    return {
        "current_step": "error",
        "logs": [f"❌ WORKFLOW FAILED: {state.get('error_message', 'Unknown error')}"]
    }

# ============ Routing Logic ============

def route_after_login(state: QMCState) -> Literal["extractor", "login", "error"]:
    """Decide next step after login."""
    if not state.get("session_cookies"): # Login failed
        if state["retry_count"] >= state["max_retries"]:
            return "error"
        return "login" # Retry
    return "extractor"

def route_after_extractor(state: QMCState) -> Literal["analyst", "error"]:
    """Decide next step after extraction."""
    if state.get("current_step") == "error":
         return "error"
    return "analyst"

# ============ Graph Construction ============

def build_graph() -> StateGraph:
    """
    Builds the Linear Multi-Agent Workflow.
    
    Flow:
    START -> LoginAgent -> ExtractorAgent -> AnalystAgent -> ReporterAgent -> END
    """
    workflow = StateGraph(QMCState)
    
    # 1. Add Agents (Nodes)
    workflow.add_node("login", login_agent)
    workflow.add_node("extractor", extractor_agent)
    workflow.add_node("analyst", analyst_agent)
    workflow.add_node("reporter", reporter_agent)
    workflow.add_node("error", error_agent)
    
    # 2. Add Edges (Connections)
    workflow.add_edge(START, "login")
    
    # Login Decision
    workflow.add_conditional_edges(
        "login",
        route_after_login,
        {
            "extractor": "extractor",
            "login": "login",
            "error": "error"
        }
    )
    
    # Extractor Decision
    workflow.add_conditional_edges(
        "extractor",
        route_after_extractor,
        {
            "analyst": "analyst",
            "error": "error"
        }
    )
    
    # Linear flow from Analyst to Reporter
    workflow.add_edge("analyst", "reporter")
    workflow.add_edge("reporter", END)
    
    # Error termination
    workflow.add_edge("error", END)
    
    return workflow

def compile_graph(checkpointer=None):
    """Compile the graph into a runnable app."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_graph().compile(checkpointer=checkpointer)