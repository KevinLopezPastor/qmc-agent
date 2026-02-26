"""
QMC Extraction Script V2 (Optimized)
Global extraction with robust filtering and pagination.
"""

import sys
import json
import time
import os
from playwright.sync_api import sync_playwright

def login_if_needed(page, args, selectors):
    """Handle login if redirected to login page."""
    try:
        # Check if already logged in (Grid visible?)
        grid_sel = selectors.get("grid", "table")
        try:
            page.wait_for_selector(grid_sel, timeout=5000)
            return True # Already logged in
        except:
            pass # Continue to login
            
        username_sel = selectors.get("username_input", "input[name='username']")
        password_sel = selectors.get("password_input", "input[name='password']")
        login_btn_sel = selectors.get("login_button", "button[type='submit']")
        
        if page.locator(username_sel).is_visible():
            page.fill(username_sel, args.get("username", ""))
            page.fill(password_sel, args.get("password", ""))
            
            if page.locator(login_btn_sel).is_visible():
                page.click(login_btn_sel)
            else:
                page.press(password_sel, "Enter")
                
            page.wait_for_load_state("networkidle")
            return True
    except Exception as e:
        print(f"Login warning: {e}")
        return False

def apply_global_filter(page, selectors):
    """Apply 'Last Execution = Today' filter."""
    try:
        last_exec_header = page.locator("th.column").filter(has_text="Last execution").first
        if last_exec_header.is_visible():
            # Open Filter
            btn = last_exec_header.locator(".qmc-filter-button button")
            if btn.is_visible():
                btn.click()
            else:
                last_exec_header.click()
            page.wait_for_timeout(1000)
            
            # Select Today (Robust)
            # Use get_by_text with exact=True to avoid matching "Last 7 days" or containers
            try:
                page.get_by_text("Today", exact=True).click()
            except:
                # Fallback to config selector if exact match fails (e.g. if inside a span)
                today_sel = selectors.get("today_option", "text=Today")
                page.locator(today_sel).first.click()
            
            page.wait_for_timeout(1000)
            
            # Close Filter
            page.keyboard.press("Escape")
            page.wait_for_timeout(2000)
            return True
    except Exception as e:
        return False

def click_show_more(page, selectors):
    """Robustly find and click 'Show more' button using multiple strategies."""
    show_more_sel = selectors.get("show_more_button", "button:has-text('Show more')")
    
    candidates = [
        page.locator(show_more_sel),
        page.get_by_role("button", name="Show more"),
        page.get_by_text("Show more", exact=False)
    ]
    
    for btn in candidates:
        try:
            if btn.count() > 1: btn = btn.last
            if btn.is_visible():
                btn.scroll_into_view_if_needed()
                btn.click(timeout=2000)
                return True
        except:
            continue
            
    # Fallback: Generic class check
    try:
        fallback = page.locator("button, .lui-button").filter(has_text="Show more").last
        if fallback.is_visible():
            fallback.click()
            return True
    except:
        pass
        
    return False

def force_scroll_bottom(page, selectors):
    """Force scroll to bottom using multiple methods to trigger lazy load."""
    table_rows_sel = selectors.get("table_rows", "tbody tr")
    
    # 1. Scroll last row (container scroll)
    try:
        rows = page.locator(table_rows_sel)
        if rows.count() > 0:
            rows.last.scroll_into_view_if_needed()
    except: pass
    
    # 2. Keyboard End
    try:
        page.keyboard.press("End")
    except: pass
    
    # 3. Mouse Wheel
    try:
        page.mouse.wheel(0, 15000)
    except: pass
    
    # 4. Window Scroll
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)

def extract_table_data(page):
    """Extract table data efficiently using JavaScript."""
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
                    const key = headers[i] || `col_${i}`;
                    rowData[key] = cell.textContent.trim();
                });
                if (Object.keys(rowData).length > 0) rows.push(rowData);
            });
            return rows;
        }
    """)

def run(playwright, args):
    browser_state_path = args.get("browser_state_path")
    headless = args.get("headless", True)
    selectors = args.get("selectors", {})
    
    # Launch Browser
    browser = playwright.chromium.launch(headless=headless)
    
    # Context (Session Reuse)
    if browser_state_path and os.path.exists(browser_state_path):
        context = browser.new_context(storage_state=browser_state_path, ignore_https_errors=True)
    else:
        context = browser.new_context(ignore_https_errors=True)
        
    page = context.new_page()
    
    try:
        # 1. Navigate & Login
        page.goto(args.get("url"))
        page.wait_for_load_state("networkidle")
        login_if_needed(page, args, selectors)
        
        # 2. Wait for Grid
        grid_sel = selectors.get("grid", "table")
        page.wait_for_selector(grid_sel, timeout=args.get("timeout", 60000))
        page.wait_for_timeout(2000)
        
        # 3. Apply Filters
        apply_global_filter(page, selectors)
        
        # 4. Pagination Loop
        max_clicks = args.get("pagination_max_clicks", 10)
        click_count = 0
        
        while click_count < max_clicks:
            force_scroll_bottom(page, selectors)
            
            if click_show_more(page, selectors):
                page.wait_for_timeout(4000) # Wait for data load
                click_count += 1
            else:
                # Double check before giving up
                page.wait_for_timeout(1000)
                if not click_show_more(page, selectors):
                    break
                    
        # 5. Extract
        data = extract_table_data(page)
        
        return {
            "success": True,
            "raw_table_data": json.dumps(data),
            "total_extracted": len(data),
            "pagination_clicks": click_count
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
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
        
    try:
        with sync_playwright() as p:
            result = run(p, args_input)
            print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Critical Error: {str(e)}"}))
