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
    print("   [QMC Extractor] Starting extraction (Global Filter)...")
    
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
    result = run_playwright_script("qmc/extract_script_v2.py", args)
    
    if not result.get("success"):
        return {
            "qmc_error": f"QMC Extraction failed: {result.get('error')}",
            "structured_data": [],
            "logs": [f"QMC Extraction Error: {result.get('error')}"]
        }
        
    raw_data_json = result.get("raw_table_data", "[]")
    total = result.get("total_extracted", 0)
    clicks = result.get("pagination_clicks", 0)
    
    log = f"QMC: Extracted {total} tasks (Pagination clicks: {clicks})"
    print(f"   [QMC Extractor] {log}")
    
    # We update raw_table_data AND pre-parse it for the next step
    return {
        "raw_table_data": raw_data_json,
        "structured_data": json.loads(raw_data_json),
        "logs": [log]
    }


# Async wrapper for compatibility if needed
async def extractor_node_async(state: QMCState) -> dict:
    return extractor_node(state)
