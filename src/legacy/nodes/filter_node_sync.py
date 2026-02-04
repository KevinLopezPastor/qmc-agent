"""
QMC Agent - Subprocess Filter Node
Runs Playwright in a completely separate process to avoid asyncio conflicts in Jupyter.
Now extracts data directly - filtering is delegated to the LLM.
"""

from datetime import datetime
from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState


def filter_node_sync(state: QMCState) -> dict:
    """
    Filter node (subprocess version): Navigates to QMC and extracts table data.
    Instead of trying to interact with complex QMC filter UI, we extract all data
    and let the LLM filter by "Last execution = Today" and "Tags = FE_HITOS".
    """
    args = {
        "url": Config.QMC_URL,
        "browser_state_path": state.get("browser_state_path"),
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.SELECTORS,
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3)
    }
    
    result = run_playwright_script("filter_script.py", args)
    
    # If we got raw_table_data, we can skip the extract step and go directly to analyze
    if result.get("raw_table_data"):
        result["current_step"] = "analyze"
    
    return result


if __name__ == "__main__":
    from src.state import create_initial_state
    
    state = create_initial_state()
    state["browser_state_path"] = "browser_state.json"
    result = filter_node_sync(state)
    print("Result keys:", result.keys())
    if result.get("raw_table_data"):
        print("Data preview:", result["raw_table_data"][:500])
