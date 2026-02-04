"""
QMC Agent - State Definition
Defines the state schema for LangGraph workflow.
"""

from typing import TypedDict, Optional, List, Literal, Annotated, Dict
from operator import add


class QMCState(TypedDict):
    """
    State schema for QMC Agent LangGraph workflow.
    
    This state is passed between nodes and persisted via MemorySaver.
    """
    
    # ========== Control Flow ==========
    current_step: Literal["init", "login", "filter", "extract", "analyze", "done", "error"]
    """Current step in the workflow."""
    
    retry_count: int
    """Number of retries attempted for current step."""
    
    max_retries: int
    """Maximum number of retries allowed (default: 3)."""
    
    # ========== Session Data ==========
    session_cookies: Optional[dict]
    """Cookies from authenticated session."""
    
    browser_state_path: Optional[str]
    """Path to saved browser state for session reuse."""
    
    # ========== Extracted Data ==========
    page_html: Optional[str]
    """Raw HTML of current page."""
    
    raw_table_data: Optional[str]
    """Raw table HTML extracted from QMC."""
    
    structured_data: Optional[List[dict]]
    """Structured JSON data after LLM processing."""
    
    process_reports: Optional[Dict]
    """Final analysis reports per process group."""
    
    report_image_path: Optional[str]
    """Path to the generated visual report image."""
    
    # ========== Error Tracking ==========
    error_message: Optional[str]
    """Last error message if any."""
    
    screenshots: Annotated[List[str], add]
    """List of screenshot paths captured during execution."""
    
    logs: Annotated[List[str], add]
    """Execution logs for debugging."""


def create_initial_state() -> QMCState:
    """Create initial state with default values."""
    return QMCState(
        current_step="init",
        retry_count=0,
        max_retries=3,
        session_cookies=None,
        browser_state_path=None,
        page_html=None,
        raw_table_data=None,
        structured_data=None,
        process_reports=None,
        report_image_path=None,
        error_message=None,
        screenshots=[],
        logs=[]
    )
