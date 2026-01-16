from playwright.sync_api import sync_playwright
import time

def verify_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Wait for server to start
            time.sleep(5)

            page.goto("http://localhost:8501")

            # Wait for title
            page.wait_for_selector("text=MedGemma Triage Console", timeout=20000)

            # Check for Sidebar Vitals
            page.wait_for_selector("text=Patient Vitals")

            # Check for Triage Button
            page.wait_for_selector("button:has-text('TRIAGE PATIENT')")

            # Take screenshot
            page.screenshot(path="verification/medgemma_ui.png", full_page=True)
            print("Screenshot saved to verification/medgemma_ui.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_app()
