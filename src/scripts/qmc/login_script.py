"""
Playwright Login Script
This script runs in a separate process to avoid asyncio conflicts.
Usage: python login_script.py '{"url": "...", "username": "...", ...}'
"""

import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright


def main():
    # Parse arguments from command line
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No arguments provided"}))
        sys.exit(1)
    
    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON arguments: {e}"}))
        sys.exit(1)
    
    url = args.get("url")
    username = args.get("username")
    password = args.get("password")
    headless = args.get("headless", True)
    timeout = args.get("timeout", 30000)
    selectors = args.get("selectors", {})
    retry_count = args.get("retry_count", 0)
    max_retries = args.get("max_retries", 3)
    
    log_entry = f"[{datetime.now().isoformat()}] LOGIN_SCRIPT: Starting authentication"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Navigate to QMC
                log_entry += f"\n  Navigating to {url}"
                page.goto(url, timeout=timeout, wait_until="networkidle")
                
                # Check if we're already logged in (Windows NTLM auth may auto-login)
                # Wait a moment for page to stabilize
                page.wait_for_timeout(2000)
                
                # Try to detect if table/grid is already visible (auto-login succeeded)
                grid_selector = selectors.get("grid", "table, tbody")
                log_entry += f"\n  Checking if already logged in..."
                
                try:
                    page.wait_for_selector(grid_selector, timeout=5000)
                    log_entry += "\n  Already logged in (Windows auth)!"
                except:
                    # Not logged in yet, need to fill credentials
                    log_entry += "\n  Not auto-logged, filling credentials..."
                    
                    username_selector = selectors.get("username_input", "input[type='text']")
                    password_selector = selectors.get("password_input", "input[type='password']")
                    
                    # Wait for login form
                    try:
                        page.wait_for_selector(username_selector, timeout=10000)
                        page.fill(username_selector, username)
                        page.fill(password_selector, password)
                        page.press(password_selector, "Enter")
                        log_entry += "\n  Credentials submitted"
                    except Exception as login_err:
                        log_entry += f"\n  Login form not found: {str(login_err)}"
                
                # Wait for page to load after login
                log_entry += "\n  Waiting for SPA to load..."
                
                # Try to hide spinner if present
                spinner_selector = selectors.get("spinner", ".spinner")
                try:
                    page.wait_for_selector(spinner_selector, state="hidden", timeout=5000)
                except:
                    pass  # Spinner might not exist
                
                # Wait for the grid/table to appear
                page.wait_for_selector(grid_selector, timeout=timeout)
                log_entry += "\n  Grid/table loaded!"
                
                # Also try waiting for actual row content
                task_row_selector = selectors.get("task_row", "tbody tr")
                try:
                    page.wait_for_selector(task_row_selector, timeout=10000)
                    log_entry += "\n  Task rows visible!"
                except:
                    log_entry += "\n  Warning: No task rows found"
                
                # Extract cookies
                cookies = context.cookies()
                session_cookies = {c["name"]: c["value"] for c in cookies}
                
                # Save browser state
                state_path = "browser_state.json"
                context.storage_state(path=state_path)
                
                log_entry += "\n  Login successful!"
                
                result = {
                    "success": True,
                    "current_step": "filter",
                    "session_cookies": session_cookies,
                    "browser_state_path": state_path,
                    "error_message": None,
                    "logs": [log_entry]
                }
                print(json.dumps(result))
                
            except Exception as e:
                # Capture screenshot on error
                screenshot_path = f"error_login_{retry_count}_{datetime.now().strftime('%H%M%S')}.png"
                try:
                    page.screenshot(path=screenshot_path)
                except:
                    screenshot_path = None
                
                error_msg = str(e)
                log_entry += f"\n  Error: {error_msg}"
                if screenshot_path:
                    log_entry += f"\n  Screenshot saved: {screenshot_path}"
                
                new_retry_count = retry_count + 1
                
                result = {
                    "success": False,
                    "current_step": "error" if new_retry_count >= max_retries else "login",
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
