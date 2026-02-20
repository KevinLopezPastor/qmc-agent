"""
NPrinting Extraction Script
Playwright script for extracting task data from NPrinting.
Usage: python extract_script.py '{"url": "...", ...}'
"""

import sys
import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright


def apply_today_filter(page):
    """Apply 'Today' filter using the NPrinting dropdown (value='t')."""
    try:
        # The correct select has ng-model="filter.dateRange.interval"
        select = page.locator("select[ng-model='filter.dateRange.interval']")
        if select.count() > 0 and select.first.is_visible(timeout=3000):
            select.first.select_option(value="t")
            page.wait_for_timeout(2000)
            return True
        return False
    except Exception:
        return False


def click_pagination_100(page):
    """Click the '100' pagination button."""
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        btn = page.locator("button:has-text('100')").first
        if btn.is_visible(timeout=2000):
            btn.click()
            page.wait_for_timeout(2000)
            return True
        return False
    except Exception:
        return False


def click_next_page(page):
    """Click 'Next' button. Returns False if no more pages."""
    try:
        btn = page.locator("a:has-text('Next')").first
        if btn.is_visible(timeout=1000):
            parent_class = btn.evaluate("el => el.parentElement?.className || ''")
            if "disabled" in parent_class:
                return False
            btn.click()
            page.wait_for_timeout(2000)
            return True
        return False
    except Exception:
        return False


def scroll_to_bottom(page):
    """Scroll to the bottom of the page."""
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.keyboard.press("End")
        page.wait_for_timeout(300)
    except Exception:
        pass


def extract_table_data(page):
    """Extract table data (Task name, Status, Progress, Created)."""
    return page.evaluate("""
        () => {
            // Get headers and map columns
            const headers = [];
            document.querySelectorAll('thead th').forEach(th => {
                headers.push(th.textContent.trim().split('\\n')[0].toLowerCase());
            });
            
            // Find column indices
            const colIdx = {
                taskName: headers.findIndex(h => h.includes('task') && h.includes('name')),
                status: headers.findIndex(h => h === 'status'),
                progress: headers.findIndex(h => h === 'progress'),
                created: headers.findIndex(h => h === 'created')
            };
            
            // Use default positions if not found
            if (colIdx.taskName === -1) colIdx.taskName = 1;
            if (colIdx.status === -1) colIdx.status = 3;
            if (colIdx.progress === -1) colIdx.progress = 4;
            if (colIdx.created === -1) colIdx.created = 5;
            
            const rows = [];
            document.querySelectorAll('tbody tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 4) return;
                
                const taskName = cells[colIdx.taskName]?.textContent.trim() || '';
                if (!taskName) return;
                
                rows.push({
                    "Task name": taskName,
                    "Status": cells[colIdx.status]?.textContent.trim() || '',
                    "Progress": cells[colIdx.progress]?.textContent.trim() || '',
                    "Created": cells[colIdx.created]?.textContent.trim() || ''
                });
            });
            
            return rows;
        }
    """)


def run(playwright, args):
    """Main extraction logic."""
    browser_state_path = args.get("nprinting_state_path", "nprinting_browser_state.json")
    headless = args.get("headless", True)
    url = args.get("url")
    timeout = args.get("timeout", 60000)
    
    browser = playwright.chromium.launch(headless=headless)
    
    if browser_state_path and os.path.exists(browser_state_path):
        context = browser.new_context(storage_state=browser_state_path, ignore_https_errors=True)
    else:
        context = browser.new_context(ignore_https_errors=True)
    
    page = context.new_page()
    
    try:
        # 1. Navigate to NPrinting
        page.goto(url, timeout=timeout, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # 2. Wait for table
        page.wait_for_selector("table", timeout=timeout)
        page.wait_for_timeout(1000)
        
        # 3. Apply Today filter
        filter_applied = apply_today_filter(page)
        
        # 4. Click 100 pagination
        scroll_to_bottom(page)
        pagination_clicked = click_pagination_100(page)
        
        # 5. Extract data from all pages
        all_data = []
        page_num = 1
        max_pages = 10
        
        while page_num <= max_pages:
            page_data = extract_table_data(page)
            if page_data:
                all_data.extend(page_data)
            
            scroll_to_bottom(page)
            
            if click_next_page(page):
                page_num += 1
            else:
                break
        
        # Deduplicate by Task name + Created
        seen = set()
        unique_data = []
        for task in all_data:
            key = (task.get("Task name", ""), task.get("Created", ""))
            if key not in seen:
                seen.add(key)
                unique_data.append(task)
        
        return {
            "success": True,
            "raw_data": json.dumps(unique_data),
            "total": len(unique_data),
            "pages_extracted": page_num,
            "filter_applied": filter_applied,
            "pagination_clicked": pagination_clicked
        }
        
    except Exception as e:
        screenshot_path = f"error_nprinting_{datetime.now().strftime('%H%M%S')}.png"
        try:
            page.screenshot(path=screenshot_path)
        except:
            screenshot_path = None
        
        return {"success": False, "error": str(e), "screenshot": screenshot_path}
        
    finally:
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No arguments provided"}))
        sys.exit(1)
    
    try:
        args_input = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)
    
    with sync_playwright() as p:
        result = run(p, args_input)
        print(json.dumps(result))
