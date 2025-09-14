from playwright.async_api import async_playwright
import asyncio

START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"]
ACTION_TIMEOUT = 15000

async def search_job_by_id(id_list: list, context):
    page = await context.new_page()
    await page.goto(START_URL)
    
    print("Please log in and navigate to a job postings page.")
    await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=300000)
    await page.wait_for_load_state('networkidle')
    
    for job_id in id_list:
        search_box = await page.wait_for_selector('input[name="emptyStateKeywordSearch"]')
        await search_box.fill('')
        await search_box.fill(job_id)
        await search_box.press('Enter')
        await page.wait_for_timeout(2000)
        
        print(f"Searching for job ID: {job_id}")
        await apply(page)

async def apply(page):
    rows = await page.locator("tbody tr.table__row--body").all()
    
    for i, row in enumerate(rows):
        playlist_add_button = row.locator('button:has-text("playlist_add"), [data-icon="playlist_add"], i:has-text("playlist_add")').first
        
        if await playlist_add_button.count() > 0:
            print(f"Row {i+1}: Clicking playlist_add button")
            await playlist_add_button.click()
            
        #    # Click radio button for "Create Custom Application Package"
        #     custom_package_radio = page.locator('input[type="radio"][value="customPkg"][name="applyOption"]').first
        #     if await custom_package_radio.count() > 0:
        #         print(f"Row {i+1}: Selecting Create Custom Application Package")
        #         try:
        #             # Try clicking the radio button directly with force
        #             await custom_package_radio.click(force=True)
        #         except:
        #             # If that fails, click the parent label instead
        #             await custom_package_radio.locator('..').click()
        #         await page.wait_for_timeout(500)
        
        #     # Click "Upload New Resume" button
        #     upload_resume_button = page.locator('button.js--btn--upload-new-doc, button:has-text("Upload New Résumé")').first
        #     if await upload_resume_button.count() > 0:
        #         print(f"Row {i+1}: Clicking Upload New Resume")
        #         await upload_resume_button.click()
        #         await page.wait_for_timeout(1000)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        
        job_ids = ["436892", "436765"]
        await search_job_by_id(job_ids, context)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())