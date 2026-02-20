"""
NPrinting Login Script
Playwright script for NPrinting authentication.
Usage: python nprinting_login_script.py '{"url": "...", "email": "...", ...}'
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
    email = args.get("email")
    password = args.get("password")
    headless = args.get("headless", True)
    timeout = args.get("timeout", 30000)
    selectors = args.get("selectors", {})
    retry_count = args.get("retry_count", 0)
    max_retries = args.get("max_retries", 3)
    
    log_entry = f"[{datetime.now().isoformat()}] NPRINTING_LOGIN: Starting authentication"
    
    try:
        with sync_playwright() as p:
            # Launch browser with SSL certificate bypass
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            
            try:
                # Navigate to NPrinting
                log_entry += f"\n  Navigating to {url}"
                page.goto(url, timeout=timeout, wait_until="networkidle")
                
                # Wait for page to stabilize
                page.wait_for_timeout(2000)
                
                # Check if we're on login page
                email_sel = selectors.get("email_input", "input[type='email']")
                password_sel = selectors.get("password_input", "input[type='password']")
                login_btn_sel = selectors.get("login_button", "button[type='submit']")
                
                log_entry += "\n  Looking for login form..."
                
                try:
                    # Wait for email field
                    page.wait_for_selector(email_sel, timeout=10000)
                    log_entry += "\n  Login form found, filling credentials..."
                    
                    # Fill email
                    page.fill(email_sel, email)
                    page.wait_for_timeout(500)
                    
                    # Fill password
                    page.fill(password_sel, password)
                    page.wait_for_timeout(500)
                    
                    log_entry += "\n  Credentials filled, looking for login button..."
                    
                    # Try multiple selectors for login button
                    login_button_selectors = [
                        login_btn_sel,
                        "button[type='submit']",
                        "button:has-text('Log in')",
                        "button:has-text('Login')",
                        "button:has-text('Sign in')",
                        "button:has-text('Iniciar')",
                        "input[type='submit']",
                        ".btn-primary",
                        "#login-button",
                        "form button",
                    ]
                    
                    button_clicked = False
                    for btn_sel in login_button_selectors:
                        try:
                            btn = page.locator(btn_sel).first
                            if btn.is_visible(timeout=1000):
                                log_entry += f"\n  Found button with selector: {btn_sel}"
                                btn.click()
                                button_clicked = True
                                log_entry += "\n  Button clicked!"
                                break
                        except:
                            continue
                    
                    # If no button found, try pressing Enter on password field
                    if not button_clicked:
                        log_entry += "\n  No button found, pressing Enter on password field..."
                        page.locator(password_sel).press("Enter")
                    
                    log_entry += "\n  Credentials submitted, waiting for redirect..."
                    
                except Exception as form_err:
                    log_entry += f"\n  Login form not found or already logged in: {str(form_err)}"
                
                # Wait for page to load after login
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                
                # Check if we're on the tasks page (look for table)
                table_sel = selectors.get("table", "table")
                try:
                    page.wait_for_selector(table_sel, timeout=timeout)
                    log_entry += "\n  Tasks table loaded - Login successful!"
                except Exception as table_err:
                    log_entry += f"\n  Warning: Table not found after login: {str(table_err)}"
                
                # Extract cookies
                cookies = context.cookies()
                session_cookies = {c["name"]: c["value"] for c in cookies}
                
                # Save browser state
                state_path = "nprinting_browser_state.json"
                context.storage_state(path=state_path)
                
                result = {
                    "success": True,
                    "current_step": "nprinting_extract",
                    "nprinting_cookies": session_cookies,
                    "nprinting_state_path": state_path,
                    "error_message": None,
                    "logs": [log_entry]
                }
                print(json.dumps(result))
                
            except Exception as e:
                # Capture screenshot on error
                screenshot_path = f"error_nprinting_login_{retry_count}_{datetime.now().strftime('%H%M%S')}.png"
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
                    "current_step": "error" if new_retry_count >= max_retries else "nprinting_login",
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
