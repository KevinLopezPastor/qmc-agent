"""
QMC Agent - Subprocess Login Node
Runs Playwright in a completely separate process to avoid asyncio conflicts.
"""

from datetime import datetime
from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState


def login_node_sync(state: QMCState) -> dict:
    """
    Login node (subprocess version): Authenticates to QMC.
    Runs Playwright in a completely separate Python process.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state dict with session cookies or error info
    """
    print("   [QMC Login] Starting authentication...")
    
    # Prepare arguments for the subprocess
    args = {
        "url": Config.QMC_URL,
        "username": Config.QMC_USERNAME,
        "password": Config.QMC_PASSWORD,
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.SELECTORS,
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3)
    }
    
    # Run the login script in a separate process
    result = run_playwright_script("qmc/login_script.py", args)
    
    # Convert error_message to qmc_error for parallel execution compatibility
    if result.get("error_message"):
        result["qmc_error"] = result.pop("error_message")
    
    # Ensure session_cookies exists (even if None) for routing
    if "session_cookies" not in result:
        result["session_cookies"] = None
    
    return result


# For testing in isolation
if __name__ == "__main__":
    from src.state import create_initial_state
    
    state = create_initial_state()
    result = login_node_sync(state)
    print("Result:", result)
