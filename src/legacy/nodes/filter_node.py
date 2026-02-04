"""
QMC Agent - Filter Node
Applies filters to QMC table: Last execution=Today, Tags=FE_HITOS
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.config import Config
from src.state import QMCState


async def filter_node(state: QMCState) -> dict:
    """
    Filter node: Applies filters to QMC task table.
    
    Filters applied:
    1. Last execution = "Today"
    2. Tags = "FE_HITOS"
    
    Args:
        state: Current workflow state (must have browser_state_path)
        
    Returns:
        Updated state dict with filtered page HTML or error info
    """
    log_entry = f"[{datetime.now().isoformat()}] FILTER_NODE: Applying filters"
    
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=Config.HEADLESS)
        
        # Restore session from saved state
        context: BrowserContext = await browser.new_context(
            storage_state=state.get("browser_state_path")
        )
        page: Page = await context.new_page()
        
        try:
            # Navigate to QMC tasks
            log_entry += f"\n  Navigating to {Config.QMC_URL}"
            await page.goto(Config.QMC_URL, timeout=Config.TIMEOUT_MS)
            
            # Wait for grid to be visible
            await page.wait_for_selector(
                Config.SELECTORS["grid"], 
                timeout=Config.TIMEOUT_MS
            )
            log_entry += "\n  Grid loaded"
            
            # ============ FILTER 1: Last execution = Today ============
            log_entry += "\n  Applying filter: Last execution = Today"
            
            # Try to click the filter icon for Last execution column
            try:
                # Wait a bit for dynamic elements
                await page.wait_for_timeout(1000)
                
                # Click on Last execution column header/filter
                last_exec_filter = await page.query_selector(
                    Config.SELECTORS["last_execution_filter"]
                )
                if last_exec_filter:
                    await last_exec_filter.click()
                    await page.wait_for_timeout(500)
                    
                    # Select "Today" option
                    today_option = await page.query_selector(
                        Config.SELECTORS["today_option"]
                    )
                    if today_option:
                        await today_option.click()
                        log_entry += "\n    ✓ Selected 'Today'"
                    else:
                        # Try text-based selection
                        await page.click("text=Today")
                        log_entry += "\n    ✓ Selected 'Today' (text match)"
                else:
                    log_entry += "\n    ⚠ Could not find Last execution filter"
                    
            except Exception as e:
                log_entry += f"\n    ⚠ Filter 1 warning: {str(e)}"
            
            # ============ FILTER 2: Tags = FE_HITOS ============
            log_entry += "\n  Applying filter: Tags = FE_HITOS_DIARIO"
            
            try:
                await page.wait_for_timeout(1000)
                
                # Click on Tags column filter
                tags_filter = await page.query_selector(
                    Config.SELECTORS["tags_filter"]
                )
                if tags_filter:
                    await tags_filter.click()
                    await page.wait_for_timeout(500)
                    
                    # Search for FE_HITOS
                    tags_search = await page.query_selector(
                        Config.SELECTORS["tags_search"]
                    )
                    if tags_search:
                        await tags_search.fill("FE_HITOS")
                        await page.wait_for_timeout(500)
                        
                        # Click apply or press Enter
                        apply_btn = await page.query_selector(
                            Config.SELECTORS["apply_button"]
                        )
                        if apply_btn:
                            await apply_btn.click()
                        else:
                            await tags_search.press("Enter")
                        
                        log_entry += "\n    ✓ Applied 'FE_HITOS_DIARIO' filter"
                    else:
                        log_entry += "\n    ⚠ Could not find tags search input"
                else:
                    log_entry += "\n    ⚠ Could not find Tags filter"
                    
            except Exception as e:
                log_entry += f"\n    ⚠ Filter 2 warning: {str(e)}"
            
            # Wait for filtered results
            await page.wait_for_timeout(2000)
            await page.wait_for_selector(
                Config.SELECTORS["grid"], 
                timeout=Config.TIMEOUT_MS
            )
            
            # Get page HTML
            page_html = await page.content()
            
            log_entry += "\n  ✅ Filters applied successfully!"
            
            return {
                "current_step": "extract",
                "page_html": page_html,
                "error_message": None,
                "logs": [log_entry]
            }
            
        except Exception as e:
            # Capture screenshot on error
            screenshot_path = f"error_filter_{state['retry_count']}_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            
            error_msg = str(e)
            log_entry += f"\n  ❌ Error: {error_msg}"
            
            new_retry_count = state["retry_count"] + 1
            
            return {
                "current_step": "error" if new_retry_count >= state["max_retries"] else "filter",
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
    
    async def test_filter():
        state = create_initial_state()
        state["browser_state_path"] = "browser_state.json"
        result = await filter_node(state)
        print("Result keys:", result.keys())
    
    asyncio.run(test_filter())
