"""
NPrinting Extractor Node
LangGraph node wrapper for NPrinting data extraction.
"""

import json
from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState


def nprinting_extractor_node(state: QMCState) -> dict:
    """
    NPrinting Extractor Node:
    - Applies 'Today' filter.
    - Clicks '100' pagination to show all records.
    - Extracts Task name, Status, Progress, Created.
    """
    print("   [NPrinting Extractor] Starting extraction...")
    
    args = {
        "url": Config.NPRINTING_URL,
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.NPRINTING_SELECTORS,
        "nprinting_state_path": state.get("nprinting_state_path", "nprinting_browser_state.json")
    }
    
    result = run_playwright_script("nprinting/extract_script.py", args)
    
    if not result.get("success"):
        print(f"   [NPrinting Extractor] Failed: {result.get('error')}")
        return {
            "nprinting_error": f"NPrinting extraction failed: {result.get('error')}",
            "nprinting_data": [],
            "logs": [f"NPrinting Extraction Error: {result.get('error')}"]
        }
    
    raw_data = result.get("raw_data", "[]")
    total = result.get("total", 0)
    filter_applied = result.get("filter_applied", False)
    pagination_clicked = result.get("pagination_clicked", False)
    
    log = f"NPrinting: Extracted {total} tasks (Filter: {filter_applied}, Pagination: {pagination_clicked})"
    print(f"   [NPrinting Extractor] {log}")
    
    return {
        "nprinting_raw_data": raw_data,
        "nprinting_data": json.loads(raw_data),
        "logs": [log]
    }


# For testing in isolation
if __name__ == "__main__":
    from src.state import create_initial_state
    
    state = create_initial_state()
    result = nprinting_extractor_node(state)
    print("Result:", json.dumps(result, indent=2))
