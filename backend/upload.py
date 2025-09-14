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
        await apply(page, job_id)

async def apply(page, job_id):
    rows = await page.locator("tbody tr.table__row--body").all()
    
    for i, row in enumerate(rows):
        playlist_add_button = row.locator('button:has-text("playlist_add"), [data-icon="playlist_add"], i:has-text("playlist_add")').first
        
        if await playlist_add_button.count() > 0:
            print(f"Row {i+1}: Clicking playlist_add button")
            # The click may open a new page or navigate within the same page. Handle both.
            app_page = page
            try:
                async with page.context.expect_page(timeout=3000) as new_page_info:
                    await playlist_add_button.click()
                app_page = await new_page_info.value
                print(f"Row {i+1}: Detected new page for application options")
            except Exception:
                await page.wait_for_load_state('networkidle')
                print(f"Row {i+1}: Stayed on same page after click")

            # Wait for the application options to appear and select the radio
            await app_page.wait_for_timeout(500)
            radio_selector = 'input[type="radio"][name="applyOption"][value="customPkg"]'

            # Try to find the radio either on the page or inside an iframe
            target_frame = None
            for frame in app_page.frames:
                try:
                    if await frame.locator(radio_selector).count() > 0:
                        target_frame = frame
                        break
                except Exception:
                    continue

            frame_or_page = target_frame if target_frame is not None else app_page

            # If we still don't have it, wait for either the radio or the container
            try:
                await frame_or_page.wait_for_selector('#applicationOptions, ' + radio_selector, timeout=20000)
            except Exception:
                print(f"Row {i+1}: application options not detected yet; continuing with best-effort selectors")

            radio = frame_or_page.locator(radio_selector)
            try:
                if await radio.count() > 0:
                    try:
                        await radio.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    if not await radio.is_checked():
                        await radio.check(force=True)
                    print(f"Row {i+1}: Checked Create Custom Application Package via input")
                else:
                    raise Exception("radio not found, trying label")
            except Exception:
                # Fallback: click the wrapping label (or its span) that contains this radio
                label = frame_or_page.locator('label:has(' + radio_selector + ")")
                if await label.count() > 0:
                    await label.first.click()
                    print(f"Row {i+1}: Clicked label wrapping the radio")
                else:
                    span_label = frame_or_page.locator('label:has(' + radio_selector + ") span.label--span, label:has-text(\"Create Custom Application Package\") span")
                    if await span_label.count() > 0:
                        await span_label.first.click()
                        print(f"Row {i+1}: Clicked span.label--span for the radio")

            # Click "Upload New Résumé" button
            upload_button = frame_or_page.locator('button.js--btn--upload-new-doc, button:has-text("Upload New Résumé")').first
            if await upload_button.count() > 0:
                print(f"Row {i+1}: Clicking Upload New Résumé")
                await upload_button.click()
                # Wait for the document name input and fill it with desired value
                doc_name_input = frame_or_page.locator('input[name="docName"]').first
                await doc_name_input.wait_for(state='visible', timeout=20000)
                await doc_name_input.fill(f"Resume + {job_id}")
                await frame_or_page.wait_for_timeout(300)
                # Click the file upload button
                file_upload_button = frame_or_page.locator('#btn_fileUploadDialog_docUpload, button#btn_fileUploadDialog_docUpload, button:has(i:has-text("file_upload"))').first
                if await file_upload_button.count() > 0:
                    print(f"Row {i+1}: Clicking file upload button")
                    await file_upload_button.click()
                    await frame_or_page.wait_for_timeout(300)
             
                file_input = frame_or_page.locator('input#fileUpload_docUpload, input[type="file"]').first
                file_path = '/Users/sohilathare/Documents/Robot Operating System (ROS).pdf'
                print(f"Row {i+1}: Setting file input: {file_path}")
                await file_input.set_input_files(file_path)
                # Submit the upload dialog
                submit_upload = frame_or_page.locator('#submitFileUploadFormBtn, button#submitFileUploadFormBtn, button:has-text("Upload A Document")').first
                if await submit_upload.count() > 0:
                    print(f"Row {i+1}: Clicking Upload A Document")
                    await submit_upload.click()
                    await frame_or_page.wait_for_load_state('networkidle')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        
        job_ids = ["436892", "436765"]
        await search_job_by_id(job_ids, context)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())