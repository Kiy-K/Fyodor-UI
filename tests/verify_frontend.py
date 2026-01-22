
import re
from playwright.sync_api import Page, expect, sync_playwright
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8503")

    try:
        # Wait for the app to be ready
        page.wait_for_load_state('networkidle')

        # Enter credentials
        page.get_by_label("Username").click()
        page.get_by_label("Username").fill("admin")
        page.get_by_label("Password").click()
        page.get_by_label("Password").fill("admin")

        # Click login
        page.get_by_role("button", name=re.compile("log in", re.IGNORECASE)).click()

        # Wait for the main app to load after login
        expect(page.get_by_text("Upload Patient Documents")).to_be_visible(timeout=20000)

        # Take screenshot
        page.screenshot(path="login_success.png")
        print("Successfully logged in and captured screenshot.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="login_fail.png")
        print("Failed to log in. Captured a failure screenshot.")

    finally:
        # ---------------------
        context.close()
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
