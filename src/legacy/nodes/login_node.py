"""
QMC Agent - Login Node
Handles authentication to QMC via Playwright.
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.config import Config
from src.state import QMCState


async def login_node(state: QMCState) -> dict:
    """
    Login node: Authenticates to QMC.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state dict with session cookies or error info
    """
    log_entry = f"[{datetime.now().isoformat()}] LOGIN_NODE: Starting authentication"
    
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=Config.HEADLESS)
        context: BrowserContext = await browser.new_context()
        page: Page = await context.new_page()
        
        try:
            # Navigate to QMC
            log_entry += f"\n  Navigating to {Config.QMC_URL}"
            await page.goto(Config.QMC_URL, timeout=Config.TIMEOUT_MS)
            
            # Wait for login form
            log_entry += "\n  Waiting for login form..."
            await page.wait_for_selector(
                Config.SELECTORS["username_input"], 
                timeout=Config.TIMEOUT_MS
            )
            
            # Fill credentials
            log_entry += "\n  Filling credentials..."
            username_input = await page.query_selector(Config.SELECTORS["username_input"])
            password_input = await page.query_selector(Config.SELECTORS["password_input"])
            
            if username_input:
                await username_input.fill(Config.QMC_USERNAME)
            if password_input:
                await password_input.fill(Config.QMC_PASSWORD)
                await password_input.press("Enter")
            
            # Wait for SPA to load (spinner disappears, grid appears)
            log_entry += "\n  Waiting for SPA to load..."
            await page.wait_for_selector(
                Config.SELECTORS["spinner"], 
                state="hidden", 
                timeout=Config.TIMEOUT_MS
            )
            await page.wait_for_selector(
                Config.SELECTORS["grid"], 
                timeout=Config.TIMEOUT_MS
            )
            
            # Extract cookies for session persistence
            cookies = await context.cookies()
            session_cookies = {c["name"]: c["value"] for c in cookies}
            
            # Save browser state for potential reuse
            state_path = "browser_state.json"
            await context.storage_state(path=state_path)
            
            log_entry += "\n  ✅ Login successful!"
            
            return {
                "current_step": "filter",
                "session_cookies": session_cookies,
                "browser_state_path": state_path,
                "error_message": None,
                "logs": [log_entry]
            }
            
        except Exception as e:
            # Capture screenshot on error
            screenshot_path = f"error_login_{state['retry_count']}_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            
            error_msg = str(e)
            log_entry += f"\n  ❌ Error: {error_msg}"
            log_entry += f"\n  Screenshot saved: {screenshot_path}"
            
            new_retry_count = state["retry_count"] + 1
            
            return {
                "current_step": "error" if new_retry_count >= state["max_retries"] else "login",
                "retry_count": new_retry_count,
                "error_message": error_msg,
                "screenshots": [screenshot_path],
                "logs": [log_entry]
            }
            
        finally:
            await browser.close()


# For testing in isolation
if __name__ == "__main__":
    from src.state import create_initial_state
    
    async def test_login():
        state = create_initial_state()
        result = await login_node(state)
        print("Result:", result)
    
    asyncio.run(test_login())
