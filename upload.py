from playwright.async_api import async_playwright
import asyncio

# URLs and File Paths
START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"]

async def search_job_by_id(id_list: list, context):
    page = await context.new_page()
    
    # Wait for user to navigate to jobs page after authentication
    await page.goto(START_URL)
    print("\n" + "="*60)
    print("Please log in and navigate to a job postings page.")
    print("The script will automatically continue once you arrive.")
    print("="*60 + "\n")

    await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=300000)
    
    print(f"\n✅ Target page detected ({page.url})! Starting job search...\n")
    
    # Wait for the page to load
    await page.wait_for_load_state('networkidle')
    
    for job_id in id_list:
        # Find and fill the search box
        search_box = await page.wait_for_selector('input[name="emptyStateKeywordSearch"]')
        
        # Clear any existing text and fill with job ID
        await search_box.fill('')  # Clear first
        await search_box.fill(job_id)
        
        # Press Enter to search
        await search_box.press('Enter')
        
        # Wait for search results to load
        await page.wait_for_timeout(2000)
        
        # Add your logic here to process the search results
        print(f"Searched for job ID: {job_id}")

async def apply():
    pass

async def main():
    async with async_playwright() as p:
        # Launch a new browser instance (same as scraper.py)
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        
        job_ids = ["436892", "436765"]  # Fixed: separate job IDs properly
        await search_job_by_id(job_ids, context)
        
        # Close the browser when done
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())