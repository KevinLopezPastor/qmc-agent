"""
QMC Agent - Extractor Node (Global V2)
Wraps the extract_script_v2.py for LangGraph.
"""

from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState
import json

def extractor_node(state: QMCState) -> dict:
    """
    Extractor Node:
    - Runs Playwright script to fetch ALL tasks for today.
    - Handles pagination automatically.
    - Returns raw list of all rows.
    """
    print("   [Extractor] Starting extraction (Global Filter)...")
    
    args = {
        "url": Config.QMC_URL,
        "username": Config.QMC_USERNAME,
        "password": Config.QMC_PASSWORD,
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.SELECTORS,
        "pagination_max_clicks": Config.PAGINATION_MAX_CLICKS,
        "browser_state_path": state.get("browser_state_path", "browser_state.json")
    }
    
    # Run the V2 script
    result = run_playwright_script("extract_script_v2.py", args)
    
    if not result.get("success"):
        return {
            "current_step": "error",
            "error_message": f"Extraction failed: {result.get('error')}",
            "logs": [f"Extraction Error: {result.get('error')}"]
        }
        
    raw_data_json = result.get("raw_table_data", "[]")
    total = result.get("total_extracted", 0)
    clicks = result.get("pagination_clicks", 0)
    
    log = f"Extracted {total} tasks (Pagination clicks: {clicks})"
    print(f"   [Extractor] {log}")
    
    # We update raw_table_data AND pre-parse it for the next step
    return {
        "current_step": "analyze",
        "raw_table_data": raw_data_json, # Keep raw for audit
        "structured_data": json.loads(raw_data_json), # Intermediate structure
        "logs": [log]
    }

# Async wrapper for compatibility if needed
async def extractor_node_async(state: QMCState) -> dict:
    return extractor_node(state)
