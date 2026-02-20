"""
QMC Agent - Graph Definition (V3.1)
Multi-Agent Workflow with QMC + NPrinting integration.
Reorganized with separated node packages.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import QMCState, create_initial_state

# Import QMC Nodes from qmc package
from src.nodes.qmc.login_node_sync import login_node_sync
from src.nodes.qmc.extractor import extractor_node
from src.nodes.qmc.analyst_llm import analyst_llm_node

# Import NPrinting Nodes from nprinting package
from src.nodes.nprinting.login_node import nprinting_login_node
from src.nodes.nprinting.extractor import nprinting_extractor_node
from src.nodes.nprinting.analyst import nprinting_analyst_node

# Import Combined/Shared Nodes
from src.nodes.combined_analyst import combined_analyst_node
from src.nodes.reporter import reporter_node


# ============ Wrappers (Async/Sync Adapters) ============

def qmc_login_agent(state: QMCState) -> dict:
    """Wrapper for QMC Login Node."""
    return login_node_sync(state)

def qmc_extractor_agent(state: QMCState) -> dict:
    """Wrapper for QMC Extractor Node."""
    return extractor_node(state)

async def qmc_analyst_agent(state: QMCState) -> dict:
    """Wrapper for QMC Analyst Node."""
    return await analyst_llm_node(state)

def nprinting_login_agent(state: QMCState) -> dict:
    """Wrapper for NPrinting Login Node."""
    return nprinting_login_node(state)

def nprinting_extractor_agent(state: QMCState) -> dict:
    """Wrapper for NPrinting Extractor Node."""
    return nprinting_extractor_node(state)

async def nprinting_analyst_agent(state: QMCState) -> dict:
    """Wrapper for NPrinting Analyst Node."""
    return await nprinting_analyst_node(state)

async def combined_analyst_agent(state: QMCState) -> dict:
    """Wrapper for Combined Analyst Node."""
    return await combined_analyst_node(state)

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

def route_after_qmc_login(state: QMCState) -> Literal["qmc_extractor", "qmc_login", "error"]:
    """Decide next step after QMC login."""
    if not state.get("session_cookies"):
        if state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "error"
        return "qmc_login"
    return "qmc_extractor"

def route_after_qmc_extractor(state: QMCState) -> Literal["qmc_analyst", "error"]:
    """Decide next step after QMC extraction."""
    if state.get("current_step") == "error":
        return "error"
    return "qmc_analyst"

def route_after_nprinting_login(state: QMCState) -> Literal["nprinting_extractor", "nprinting_login", "error"]:
    """Decide next step after NPrinting login."""
    if not state.get("nprinting_cookies"):
        if state.get("nprinting_retry_count", 0) >= state.get("max_retries", 3):
            return "error"
        return "nprinting_login"
    return "nprinting_extractor"

def route_after_nprinting_extractor(state: QMCState) -> Literal["nprinting_analyst", "error"]:
    """Decide next step after NPrinting extraction."""
    if state.get("current_step") == "error":
        return "error"
    return "nprinting_analyst"


# ============ Sync Node for Parallel Join ============

def sync_node(state: QMCState) -> dict:
    """
    Synchronization point - combines results from parallel QMC and NPrinting flows.
    """
    qmc_count = len(state.get("process_reports", {}) or {})
    nprinting_count = len(state.get("nprinting_reports", {}) or {})
    
    return {
        "logs": [f"🔄 Sync: QMC({qmc_count}) + NPrinting({nprinting_count})"]
    }


# ============ Graph Construction ============

def build_unified_graph() -> StateGraph:
    """
    Builds the Unified Multi-Agent Workflow with QMC + NPrinting.
    
    Architecture:
        START
          ├─────────────────────────────────┐
          ▼                                 ▼
    [QMC Login]                     [NPrinting Login]
          │                                 │
          ▼                                 ▼
    [QMC Extractor]                 [NPrinting Extractor]
          │                                 │
          ▼                                 ▼
    [QMC Analyst]                   [NPrinting Analyst]
          │                                 │
          └────────────┬────────────────────┘
                       ▼
               [Combined Analyst]
                       │
                       ▼
                  [Reporter]
                       │
                       ▼
                      END
    """
    workflow = StateGraph(QMCState)
    
    # 1. Add All Nodes
    # QMC Flow
    workflow.add_node("qmc_login", qmc_login_agent)
    workflow.add_node("qmc_extractor", qmc_extractor_agent)
    workflow.add_node("qmc_analyst", qmc_analyst_agent)
    
    # NPrinting Flow
    workflow.add_node("nprinting_login", nprinting_login_agent)
    workflow.add_node("nprinting_extractor", nprinting_extractor_agent)
    workflow.add_node("nprinting_analyst", nprinting_analyst_agent)
    
    # Combined Flow
    workflow.add_node("sync", sync_node)
    workflow.add_node("combined_analyst", combined_analyst_agent)
    workflow.add_node("reporter", reporter_agent)
    workflow.add_node("error", error_agent)
    
    # 2. Parallel Start
    workflow.add_edge(START, "qmc_login")
    workflow.add_edge(START, "nprinting_login")
    
    # 3. QMC Flow Edges
    workflow.add_conditional_edges(
        "qmc_login",
        route_after_qmc_login,
        {
            "qmc_extractor": "qmc_extractor",
            "qmc_login": "qmc_login",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "qmc_extractor",
        route_after_qmc_extractor,
        {
            "qmc_analyst": "qmc_analyst",
            "error": "error"
        }
    )
    workflow.add_edge("qmc_analyst", "sync")
    
    # 4. NPrinting Flow Edges
    workflow.add_conditional_edges(
        "nprinting_login",
        route_after_nprinting_login,
        {
            "nprinting_extractor": "nprinting_extractor",
            "nprinting_login": "nprinting_login",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "nprinting_extractor",
        route_after_nprinting_extractor,
        {
            "nprinting_analyst": "nprinting_analyst",
            "error": "error"
        }
    )
    workflow.add_edge("nprinting_analyst", "sync")
    
    # 5. Combined Flow
    workflow.add_edge("sync", "combined_analyst")
    workflow.add_edge("combined_analyst", "reporter")
    workflow.add_edge("reporter", END)
    
    # 6. Error termination
    workflow.add_edge("error", END)
    
    return workflow


def compile_unified_graph(checkpointer=None):
    """Compile the unified graph into a runnable app."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_unified_graph().compile(checkpointer=checkpointer)


# ============ Legacy Graph (QMC Only) ============

def build_graph() -> StateGraph:
    """
    Legacy: Builds QMC-only workflow for backwards compatibility.
    """
    workflow = StateGraph(QMCState)
    
    workflow.add_node("login", qmc_login_agent)
    workflow.add_node("extractor", qmc_extractor_agent)
    workflow.add_node("analyst", qmc_analyst_agent)
    workflow.add_node("reporter", reporter_agent)
    workflow.add_node("error", error_agent)
    
    workflow.add_edge(START, "login")
    workflow.add_conditional_edges(
        "login",
        route_after_qmc_login,
        {
            "qmc_extractor": "extractor",
            "qmc_login": "login",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "extractor",
        route_after_qmc_extractor,
        {
            "qmc_analyst": "analyst",
            "error": "error"
        }
    )
    workflow.add_edge("analyst", "reporter")
    workflow.add_edge("reporter", END)
    workflow.add_edge("error", END)
    
    return workflow


def compile_graph(checkpointer=None):
    """Compile the legacy QMC-only graph."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_graph().compile(checkpointer=checkpointer)