"""
Playwright Filter/Extract Script - Optimized Version
Applies UI filters in QMC and extracts filtered table data.
Usage: python filter_script.py '{"url": "...", "browser_state_path": "...", ...}'
"""

import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright


def apply_tags_filter(page, tag_value: str, log_entries: list) -> bool:
    """Apply filter on Tags column."""
    try:
        # Find and click Tags filter button
        tags_header = page.locator("th.column").filter(has_text="Tags").first
        tags_header.locator(".qmc-filter-button button").click()
        log_entries.append(f"Clicked Tags filter")
        page.wait_for_timeout(1000)
        
        # Type in search input and click the matching option
        search_input = page.locator("input").first
        search_input.fill(tag_value)
        log_entries.append(f"Typed '{tag_value}'")
        page.wait_for_timeout(800)
        
        # Click checkbox to select
        checkbox = page.locator("input[type='checkbox']").first
        if checkbox.is_visible():
            checkbox.click()
            log_entries.append("Selected checkbox")
        else:
            page.locator(f"text={tag_value}").first.click()
            log_entries.append("Clicked option text")
        
        page.wait_for_timeout(1500)
        return True
    except Exception as e:
        log_entries.append(f"Tags filter error: {str(e)}")
        return False


def apply_date_filter(page, date_option: str, log_entries: list) -> bool:
    """Apply filter on Last execution column."""
    try:
        # Find and click Last execution filter button
        last_exec_header = page.locator("th.column").filter(has_text="Last execution").first
        last_exec_header.locator(".qmc-filter-button button").click()
        log_entries.append(f"Clicked Last execution filter")
        page.wait_for_timeout(1000)
        
        # Click date option (e.g., "Today")
        page.locator(f"text={date_option}").first.click()
        log_entries.append(f"Selected '{date_option}'")
        page.wait_for_timeout(1500)
        return True
    except Exception as e:
        log_entries.append(f"Date filter error: {str(e)}")
        return False


def extract_table_data(page) -> dict:
    """Extract table data using JavaScript."""
    return page.evaluate("""
        () => {
            const headers = [];
            document.querySelectorAll('thead th').forEach(th => {
                headers.push(th.textContent.trim().split('\\n')[0]);
            });
            
            const rows = [];
            document.querySelectorAll('tbody tr').forEach(row => {
                const rowData = {};
                row.querySelectorAll('td').forEach((cell, i) => {
                    rowData[headers[i] || `col_${i}`] = cell.textContent.trim();
                });
                if (Object.keys(rowData).length > 0) rows.push(rowData);
            });
            
            return { headers, rows, totalRows: rows.length };
        }
    """)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No arguments provided"}))
        sys.exit(1)
    
    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)
    
    url = args.get("url")
    browser_state_path = args.get("browser_state_path")
    headless = args.get("headless", True)
    timeout = args.get("timeout", 30000)
    selectors = args.get("selectors", {})
    
    log_entries = []
    today_str = datetime.now().strftime("%d_%m")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=browser_state_path)
            page = context.new_page()
            
            try:
                # Navigate to QMC
                page.goto(url, timeout=timeout, wait_until="networkidle")
                page.wait_for_selector(selectors.get("grid", "table"), timeout=timeout)
                page.wait_for_timeout(2000)
                log_entries.append("Page loaded")
                
                # Apply filters
                apply_tags_filter(page, "FE_HITOS_DIARIO", log_entries)
                apply_date_filter(page, "Today", log_entries)
                
                # Wait for filtered results
                page.wait_for_timeout(2000)
                page.screenshot(path=f"./debug/filter_result_{today_str}.png")
                
                # Extract data
                table_data = extract_table_data(page)
                log_entries.append(f"Extracted {table_data['totalRows']} rows")
                
                result = {
                    "success": True,
                    "current_step": "extract",
                    "raw_table_data": json.dumps(table_data, indent=2, ensure_ascii=False),
                    "page_html": page.content(),
                    "error_message": None,
                    "logs": [f"[{datetime.now().isoformat()}] " + " | ".join(log_entries)]
                }
                print(json.dumps(result))
                
            except Exception as e:
                page.screenshot(path=f"./debug/error_{today_str}.png")
                result = {
                    "success": False,
                    "current_step": "error",
                    "error_message": str(e),
                    "logs": [f"[{datetime.now().isoformat()}] Error: {e}"]
                }
                print(json.dumps(result))
                
            finally:
                browser.close()
                
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error_message": f"Playwright init failed: {e}",
            "logs": [f"[{datetime.now().isoformat()}] FATAL: {e}"]
        }))


if __name__ == "__main__":
    main()
