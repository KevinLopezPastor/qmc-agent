"""
QMC Filter Debug Script - With Login
This script runs with headless=False to help identify the correct filter selectors.
Run this directly: python src/scripts/debug_filters.py
"""

import json
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright


def main():
    print("=" * 60)
    print("QMC FILTER DEBUG SCRIPT - WITH LOGIN")
    print("=" * 60)
    print("\nThis will open a visible browser to inspect the QMC filters.")
    print("Screenshots will be saved at each step.\n")
    
    # Load config
    sys.path.insert(0, '.')
    from src.config import Config
    
    url = Config.QMC_URL
    username = Config.QMC_USERNAME
    password = Config.QMC_PASSWORD
    
    print(f"URL: {url}")
    print(f"Username: {username}")
    
    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # Step 1: Navigate
            print("\n[1] Navigating to QMC...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            page.screenshot(path="debug_01_initial.png")
            print("    Screenshot: debug_01_initial.png")
            
            # Step 2: Login if needed
            print("\n[2] Checking if login is needed...")
            login_input = page.query_selector("input[placeholder*='user'], input[name='username']")
            if login_input:
                print("    Login form detected, filling credentials...")
                login_input.fill(username)
                
                password_input = page.query_selector("input[type='password']")
                if password_input:
                    password_input.fill(password)
                
                # Click login button
                login_btn = page.query_selector("button:has-text('Log in'), button[type='submit'], input[type='submit']")
                if login_btn:
                    print("    Clicking login button...")
                    login_btn.click()
                else:
                    # Try pressing Enter
                    password_input.press("Enter")
                
                print("    Waiting for login to complete...")
                page.wait_for_timeout(5000)
                page.screenshot(path="debug_02_after_login.png")
                print("    Screenshot: debug_02_after_login.png")
            else:
                print("    No login form, already authenticated")
            
            # Step 3: Wait for table to load
            print("\n[3] Waiting for table to load...")
            page.wait_for_timeout(5000)
            page.screenshot(path="debug_03_table_loading.png")
            print("    Screenshot: debug_03_table_loading.png")
            
            # Try to find the table
            table_selectors = ["table", "tbody", "[class*='grid']", "[class*='table']", "[class*='list']"]
            for sel in table_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    print(f"    Found {len(elements)} elements for: {sel}")
            
            # Step 4: Find column headers
            print("\n[4] Searching for column headers...")
            
            # Try multiple header selectors
            header_selectors = [
                "th",
                "thead td",
                ".header-cell",
                "[class*='header']",
                "[role='columnheader']"
            ]
            
            for sel in header_selectors:
                headers = page.query_selector_all(sel)
                if headers:
                    print(f"\n    Found {len(headers)} headers with selector: {sel}")
                    for i, h in enumerate(headers[:12]):
                        text = h.inner_text().strip().replace("\n", " ")[:40]
                        classes = h.get_attribute("class") or ""
                        print(f"      [{i}] '{text}' class='{classes[:40]}'")
            
            # Step 5: Look for "Last execution" header and click
            print("\n[5] Looking for 'Last execution' column...")
            
            # Try to find by text content
            last_exec = page.query_selector("th:has-text('Last execution')")
            if not last_exec:
                last_exec = page.query_selector("td:has-text('Last execution')")
            if not last_exec:
                # Try text locator
                last_exec = page.locator("text=Last execution").first
                if last_exec.count() == 0:
                    last_exec = None
            
            if last_exec:
                print("    Found 'Last execution'!")
                # Get parent to find the clickable header
                try:
                    last_exec.click()
                    print("    Clicked on 'Last execution' header")
                    page.wait_for_timeout(2000)
                    page.screenshot(path="debug_04_last_exec_clicked.png")
                    print("    Screenshot: debug_04_last_exec_clicked.png")
                except Exception as e:
                    print(f"    Click failed: {e}")
            else:
                print("    'Last execution' not found")
            
            # Step 6: Look for Tags column and click
            print("\n[6] Looking for 'Tags' column...")
            tags = page.query_selector("th:has-text('Tags')")
            if not tags:
                tags = page.locator("text=Tags").first
                if tags.count() == 0:
                    tags = None
            
            if tags:
                print("    Found 'Tags'!")
                try:
                    tags.click()
                    print("    Clicked on 'Tags' header")
                    page.wait_for_timeout(2000)
                    page.screenshot(path="debug_05_tags_clicked.png")
                    print("    Screenshot: debug_05_tags_clicked.png")
                except Exception as e:
                    print(f"    Click failed: {e}")
            else:
                print("    'Tags' not found")
            
            # Step 7: Look for filter/search UI elements
            print("\n[7] Looking for filter UI elements...")
            
            filter_selectors = [
                "input[type='search']",
                "input[placeholder*='search']",
                "input[placeholder*='filter']",
                "[class*='filter']",
                "[class*='Filter']",
                ".lui-search",
                ".lui-icon--search",
                ".lui-filterbox"
            ]
            
            for sel in filter_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    print(f"    Found {len(elements)} elements for: {sel}")
                    for i, el in enumerate(elements[:5]):
                        classes = el.get_attribute("class") or ""
                        placeholder = el.get_attribute("placeholder") or ""
                        tag = el.evaluate("el => el.tagName")
                        print(f"      [{i}] <{tag}> class='{classes[:40]}' placeholder='{placeholder}'")
            
            # Step 8: Look for dropdown/menu elements
            print("\n[8] Looking for dropdowns/menus...")
            dropdown_selectors = [
                ".dropdown",
                ".menu", 
                "[class*='popup']",
                "[class*='Popup']",
                ".lui-popover",
                ".lui-menu"
            ]
            
            for sel in dropdown_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    print(f"    Found {len(elements)} elements for: {sel}")
            
            # Step 9: Get HTML structure of header row
            print("\n[9] Capturing HTML structure...")
            try:
                thead = page.query_selector("thead")
                if thead:
                    html = thead.inner_html()
                    with open("debug_thead.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("    Saved thead to: debug_thead.html")
                
                # Also get any row to see structure
                first_row = page.query_selector("tbody tr")
                if first_row:
                    html = first_row.inner_html()
                    with open("debug_row.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("    Saved first row to: debug_row.html")
            except Exception as e:
                print(f"    Error capturing HTML: {e}")
            
            # Step 10: Final screenshot
            print("\n[10] Taking final screenshot...")
            page.screenshot(path="debug_10_final.png", full_page=True)
            print("    Screenshot: debug_10_final.png")
            
            print("\n" + "=" * 60)
            print("DEBUG COMPLETE")
            print("=" * 60)
            print("\nPlease check the screenshots and HTML files.")
            print("The browser will stay open for 60 seconds for manual inspection.")
            print("Try clicking on the column headers manually to see how filtering works!")
            print("\nPress Ctrl+C to close the browser.\n")
            
            # Keep browser open for manual inspection
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\nClosing browser...")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="debug_error.png")
            print("Error screenshot: debug_error.png")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
