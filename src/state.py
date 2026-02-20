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
    
    # ========== QMC Session Data ==========
    session_cookies: Optional[dict]
    """Cookies from authenticated QMC session."""
    
    browser_state_path: Optional[str]
    """Path to saved browser state for session reuse."""
    
    # ========== QMC Extracted Data ==========
    page_html: Optional[str]
    """Raw HTML of current page."""
    
    raw_table_data: Optional[str]
    """Raw table HTML extracted from QMC."""
    
    structured_data: Optional[List[dict]]
    """Structured JSON data after LLM processing."""
    
    process_reports: Optional[Dict]
    """Final analysis reports per QMC process group."""
    
    # ========== NPrinting Session Data ==========
    nprinting_cookies: Optional[dict]
    """Cookies from authenticated NPrinting session."""
    
    nprinting_state_path: Optional[str]
    """Path to saved NPrinting browser state."""
    
    nprinting_retry_count: int
    """Number of retries for NPrinting operations."""
    
    # ========== NPrinting Extracted Data ==========
    nprinting_raw_data: Optional[str]
    """Raw table data extracted from NPrinting."""
    
    nprinting_data: Optional[List[dict]]
    """Structured JSON data from NPrinting."""
    
    nprinting_reports: Optional[Dict]
    """Analysis reports per NPrinting process group."""
    
    # ========== Combined Data ==========
    combined_report: Optional[Dict]
    """Combined analysis from QMC + NPrinting."""
    
    # ========== Output ==========
    report_image_path: Optional[str]
    """Path to the generated visual report image."""
    
    # ========== Error Tracking ==========
    error_message: Optional[str]
    """Last error message if any (used by combined/reporter nodes)."""
    
    qmc_error: Optional[str]
    """Error message from QMC flow."""
    
    nprinting_error: Optional[str]
    """Error message from NPrinting flow."""
    
    screenshots: Annotated[List[str], add]
    """List of screenshot paths captured during execution."""
    
    logs: Annotated[List[str], add]
    """Execution logs for debugging."""


def create_initial_state() -> QMCState:
    """Create initial state with default values."""
    return QMCState(
        # Control
        current_step="init",
        retry_count=0,
        max_retries=3,
        # QMC
        session_cookies=None,
        browser_state_path=None,
        page_html=None,
        raw_table_data=None,
        structured_data=None,
        process_reports=None,
        # NPrinting
        nprinting_cookies=None,
        nprinting_state_path=None,
        nprinting_retry_count=0,
        nprinting_raw_data=None,
        nprinting_data=None,
        nprinting_reports=None,
        # Combined
        combined_report=None,
        # Output
        report_image_path=None,
        # Error
        error_message=None,
        qmc_error=None,
        nprinting_error=None,
        screenshots=[],
        logs=[]
    )

