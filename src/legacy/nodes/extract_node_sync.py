"""
QMC Agent - Subprocess Extract Node
Runs Playwright in a completely separate process to avoid asyncio conflicts in Jupyter.
"""

import re
from datetime import datetime
from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState


def extract_table_from_html(html: str) -> str:
    """Extract table content from full page HTML."""
    patterns = [
        r'<div[^>]*class="[^"]*qmc-grid[^"]*"[^>]*>(.*?)</div>',
        r'<table[^>]*class="[^"]*qmc-grid[^"]*"[^>]*>(.*?)</table>',
        r'<tbody[^>]*>(.*?)</tbody>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0)
    
    return html[:10000] if len(html) > 10000 else html


def extract_node_sync(state: QMCState) -> dict:
    """
    Extract node (subprocess version): Extracts table data from QMC.
    Runs Playwright in a completely separate Python process.
    """
    # If we already have page HTML, extract from it directly (no subprocess needed)
    if state.get("page_html"):
        log_entry = f"[{datetime.now().isoformat()}] EXTRACT_NODE: Using page HTML from previous node"
        table_html = extract_table_from_html(state["page_html"])
        
        if table_html:
            log_entry += f"\n  Extracted table ({len(table_html)} chars)"
            return {
                "success": True,
                "current_step": "analyze",
                "raw_table_data": table_html,
                "error_message": None,
                "logs": [log_entry]
            }
    
    # Otherwise, run the extract script in subprocess
    args = {
        "url": Config.QMC_URL,
        "browser_state_path": state.get("browser_state_path"),
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.SELECTORS,
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3)
    }
    
    result = run_playwright_script("extract_script.py", args)
    return result


if __name__ == "__main__":
    from src.state import create_initial_state
    
    state = create_initial_state()
    state["browser_state_path"] = "browser_state.json"
    result = extract_node_sync(state)
    print("Result keys:", result.keys())
