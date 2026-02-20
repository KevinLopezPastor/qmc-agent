"""
NPrinting Login Node
LangGraph node wrapper for NPrinting authentication.
"""

from src.playwright_runner import run_playwright_script
from src.config import Config
from src.state import QMCState


def nprinting_login_node(state: QMCState) -> dict:
    """
    NPrinting Login Node:
    - Authenticates to NPrinting using email/password.
    - Saves session cookies and browser state.
    - Runs in subprocess to avoid asyncio conflicts.
    """
    print("   [NPrinting Login] Starting authentication...")
    
    args = {
        "url": Config.NPRINTING_URL,
        "email": Config.NPRINTING_EMAIL,
        "password": Config.NPRINTING_PASSWORD,
        "headless": Config.HEADLESS,
        "timeout": Config.TIMEOUT_MS,
        "selectors": Config.NPRINTING_SELECTORS,
        "retry_count": state.get("nprinting_retry_count", 0),
        "max_retries": state.get("max_retries", 3)
    }
    
    result = run_playwright_script("nprinting/login_script.py", args)
    
    if result.get("success"):
        print("   [NPrinting Login] Authentication successful!")
        return {
            "nprinting_cookies": result.get("nprinting_cookies"),
            "nprinting_state_path": result.get("nprinting_state_path"),
            "logs": result.get("logs", [])
        }
    else:
        print(f"   [NPrinting Login] Failed: {result.get('error_message')}")
        return {
            "nprinting_retry_count": result.get("retry_count", 0),
            "nprinting_error": result.get("error_message"),
            "nprinting_cookies": None,
            "logs": result.get("logs", [])
        }


# For testing in isolation
if __name__ == "__main__":
    from src.state import create_initial_state
    
    state = create_initial_state()
    result = nprinting_login_node(state)
    print("Result:", result)
