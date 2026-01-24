
import re
from playwright.sync_api import Page, expect, sync_playwright
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8501")

    try:
        # Wait for the app to be ready
        page.wait_for_load_state('networkidle')

        # Enter credentials
        page.get_by_label("Username").fill("admin")
        page.get_by_role("textbox", name="Password").fill("admin123")

        # Click login
        login_button = page.get_by_role("button", name=re.compile(r"login", re.IGNORECASE))
        login_button.wait_for(state="visible")
        login_button.click()

        # Wait for the main app to load after login
        expect(page.get_by_text("Upload Clinical Documents (PDF, DOCX, Images)")).to_be_visible(timeout=20000)

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
