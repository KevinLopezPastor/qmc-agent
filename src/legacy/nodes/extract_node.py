"""
QMC Agent - Extract Node
Extracts table data from filtered QMC page.
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.config import Config
from src.state import QMCState


async def extract_node(state: QMCState) -> dict:
    """
    Extract node: Extracts table data from QMC.
    
    Can work in two modes:
    1. From page_html in state (if filter_node provided it)
    2. Fresh navigation with session restoration
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state dict with raw_table_data or error info
    """
    log_entry = f"[{datetime.now().isoformat()}] EXTRACT_NODE: Extracting table data"
    
    # If we already have page HTML, extract from it
    if state.get("page_html"):
        log_entry += "\n  Using page HTML from previous node"
        table_html = extract_table_from_html(state["page_html"])
        
        if table_html:
            log_entry += f"\n  ✅ Extracted table ({len(table_html)} chars)"
            return {
                "current_step": "analyze",
                "raw_table_data": table_html,
                "error_message": None,
                "logs": [log_entry]
            }
    
    # Otherwise, navigate fresh
    log_entry += "\n  Navigating to extract fresh data"
    
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=Config.HEADLESS)
        
        context: BrowserContext = await browser.new_context(
            storage_state=state.get("browser_state_path")
        )
        page: Page = await context.new_page()
        
        try:
            await page.goto(Config.QMC_URL, timeout=Config.TIMEOUT_MS)
            
            # Wait for grid
            await page.wait_for_selector(
                Config.SELECTORS["grid"], 
                timeout=Config.TIMEOUT_MS
            )
            
            # Extract table data using JavaScript
            table_data = await page.evaluate("""
                () => {
                    const grid = document.querySelector('.qmc-grid');
                    if (!grid) return null;
                    
                    const rows = [];
                    const tableRows = grid.querySelectorAll('tbody tr, .grid-row');
                    
                    tableRows.forEach(row => {
                        const cells = row.querySelectorAll('td, .grid-cell');
                        const rowData = {};
                        
                        cells.forEach((cell, index) => {
                            const header = cell.getAttribute('data-column') || 
                                          document.querySelectorAll('th')[index]?.textContent?.trim() ||
                                          `column_${index}`;
                            rowData[header] = cell.textContent.trim();
                        });
                        
                        if (Object.keys(rowData).length > 0) {
                            rows.push(rowData);
                        }
                    });
                    
                    return JSON.stringify(rows, null, 2);
                }
            """)
            
            # Also get raw HTML as backup
            grid_element = await page.query_selector(Config.SELECTORS["grid"])
            raw_html = await grid_element.inner_html() if grid_element else ""
            
            # Combine into structured raw data
            raw_table_data = f"""
=== EXTRACTED TABLE DATA ===
{table_data if table_data else 'No structured data extracted'}

=== RAW HTML ===
{raw_html[:5000] if raw_html else 'No HTML extracted'}
"""
            
            log_entry += f"\n  ✅ Extracted {len(raw_table_data)} chars of data"
            
            return {
                "current_step": "analyze",
                "raw_table_data": raw_table_data,
                "error_message": None,
                "logs": [log_entry]
            }
            
        except Exception as e:
            screenshot_path = f"error_extract_{state['retry_count']}_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            
            error_msg = str(e)
            log_entry += f"\n  ❌ Error: {error_msg}"
            
            new_retry_count = state["retry_count"] + 1
            
            return {
                "current_step": "error" if new_retry_count >= state["max_retries"] else "extract",
                "retry_count": new_retry_count,
                "error_message": error_msg,
                "screenshots": [screenshot_path],
                "logs": [log_entry]
            }
            
        finally:
            await browser.close()


def extract_table_from_html(html: str) -> str:
    """
    Extract table content from full page HTML.
    
    Args:
        html: Full page HTML
        
    Returns:
        Table HTML or empty string
    """
    # Try to find qmc-grid content
    patterns = [
        r'<div[^>]*class="[^"]*qmc-grid[^"]*"[^>]*>(.*?)</div>',
        r'<table[^>]*class="[^"]*qmc-grid[^"]*"[^>]*>(.*?)</table>',
        r'<tbody[^>]*>(.*?)</tbody>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0)
    
    # Return truncated HTML if no specific table found
    return html[:10000] if len(html) > 10000 else html


# For testing
if __name__ == "__main__":
    from src.state import create_initial_state
    
    async def test_extract():
        state = create_initial_state()
        state["browser_state_path"] = "browser_state.json"
        result = await extract_node(state)
        print("Result keys:", result.keys())
        if result.get("raw_table_data"):
            print("Data length:", len(result["raw_table_data"]))
    
    asyncio.run(test_extract())
