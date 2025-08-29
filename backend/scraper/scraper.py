# scraper.py

import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables from the .env file
load_dotenv()

# Get credentials from environment variables
WW_USERNAME = os.getenv("WW_USERNAME")
WW_PASSWORD = os.getenv("WW_PASSWORD")

# Check if credentials are set
if not WW_USERNAME or not WW_PASSWORD:
    raise ValueError("WaterlooWorks username and password must be set in the .env file")

LOGIN_URL = "https://waterlooworks.uwaterloo.ca/myAccount/dashboard.htm"

async def main():
    """
    Main function to log in to WaterlooWorks and take a screenshot of the dashboard.
    """
    async with async_playwright() as p:
        # We launch the browser. headless=False means we can see the browser window.
        # This is essential for debugging during development.
        browser = await p.chromium.launch(headless=False, slow_mo=50) # slow_mo adds a small delay
        
        page = await browser.new_page()
        
        print("Navigating to WaterlooWorks login page...")
        await page.goto(LOGIN_URL)
        
        # The page automatically redirects to the Microsoft login
        print("Waiting for Microsoft login page to load...")
        
        # Use locators to find the input fields and fill them
        # Playwright will automatically wait for these elements to appear
        print(f"Entering username: {WW_USERNAME}")
        await page.locator('input[name="loginfmt"]').fill(WW_USERNAME)
        await page.locator('input[type="submit"]').click()
        
        print("Entering password...")
        await page.locator('input[name="passwd"]').fill(WW_PASSWORD)
        await page.locator('input[type="submit"]').click()
        
        # After submitting password, we need to handle the "Stay signed in?" prompt
        print("Handling 'Stay signed in?' prompt...")
        # We click the "No" button to ensure a clean session every time
        await page.locator('input[type="button"][value="No"]').click()
        
        # Now, we verify that the login was successful by waiting for the dashboard URL
        print("Waiting for dashboard to load...")
        await page.wait_for_url("**/myAccount/dashboard.htm", timeout=60000) # Wait up to 60s
        
        print("Successfully logged in! Taking a screenshot...")
        await page.screenshot(path="dashboard_screenshot.png")
        
        print("Screenshot saved as 'dashboard_screenshot.png'.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())