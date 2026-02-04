"""
Playwright Extract Script
This script runs in a separate process to avoid asyncio conflicts.
Usage: python extract_script.py '{"url": "...", "browser_state_path": "...", ...}'
"""

import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No arguments provided"}))
        sys.exit(1)
    
    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON arguments: {e}"}))
        sys.exit(1)
    
    url = args.get("url")
    browser_state_path = args.get("browser_state_path")
    headless = args.get("headless", True)
    timeout = args.get("timeout", 30000)
    selectors = args.get("selectors", {})
    retry_count = args.get("retry_count", 0)
    max_retries = args.get("max_retries", 3)
    
    log_entry = f"[{datetime.now().isoformat()}] EXTRACT_SCRIPT: Extracting table data"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=browser_state_path)
            page = context.new_page()
            
            try:
                page.goto(url, timeout=timeout)
                
                grid_selector = selectors.get("grid", ".qmc-grid")
                page.wait_for_selector(grid_selector, timeout=timeout)
                
                # Extract table data using JavaScript
                table_data = page.evaluate("""
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
                
                # Get raw HTML as backup
                grid_element = page.query_selector(grid_selector)
                raw_html = grid_element.inner_html() if grid_element else ""
                
                raw_table_data = f"""
=== EXTRACTED TABLE DATA ===
{table_data if table_data else 'No structured data extracted'}

=== RAW HTML ===
{raw_html[:5000] if raw_html else 'No HTML extracted'}
"""
                
                log_entry += f"\n  Extracted {len(raw_table_data)} chars of data"
                
                result = {
                    "success": True,
                    "current_step": "analyze",
                    "raw_table_data": raw_table_data,
                    "error_message": None,
                    "logs": [log_entry]
                }
                print(json.dumps(result))
                
            except Exception as e:
                screenshot_path = f"error_extract_{retry_count}_{datetime.now().strftime('%H%M%S')}.png"
                try:
                    page.screenshot(path=screenshot_path)
                except:
                    screenshot_path = None
                
                error_msg = str(e)
                log_entry += f"\n  Error: {error_msg}"
                
                new_retry_count = retry_count + 1
                
                result = {
                    "success": False,
                    "current_step": "error" if new_retry_count >= max_retries else "extract",
                    "retry_count": new_retry_count,
                    "error_message": error_msg,
                    "screenshots": [screenshot_path] if screenshot_path else [],
                    "logs": [log_entry]
                }
                print(json.dumps(result))
                
            finally:
                browser.close()
                
    except Exception as e:
        result = {
            "success": False,
            "error_message": f"Playwright initialization failed: {str(e)}",
            "logs": [f"[{datetime.now().isoformat()}] FATAL: {str(e)}"]
        }
        print(json.dumps(result))


if __name__ == "__main__":
    main()
