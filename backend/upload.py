from playwright.async_api import async_playwright
import asyncio
import os

START_URL = "https://waterlooworks.uwaterloo.ca/myAccount/co-op/full/jobs.htm"
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm"]
ACTION_TIMEOUT = 15000
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")
STORAGE_STATE_FILE = os.path.join(OUTPUTS_DIR, "storage_state.json")

async def search_job_by_id(id_list: list, context, out_dir: str | None = None):
    page = await context.new_page()
    await page.goto(START_URL)
    
    print("Please log in. I'll redirect you to the job postings page after login.")
    # Wait until we're back on any authenticated myAccount page
    await page.wait_for_url(lambda url: "/myAccount/" in url, timeout=300000)
    # Ensure we land on the jobs page specifically
    await page.goto(START_URL)
    await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=60000)
    await page.wait_for_load_state('networkidle')
    
    for job_id in id_list:
        # Determine personalized PDF paths if provided
        resume_path = None
        cover_path = None
        if out_dir:
            try:
                rp = os.path.join(out_dir, f"{job_id}_resume.pdf")
                cp = os.path.join(out_dir, f"{job_id}_cover_letter.pdf")
                if os.path.exists(rp):
                    resume_path = rp
                if os.path.exists(cp):
                    cover_path = cp
            except Exception:
                pass
        search_box = await page.wait_for_selector('input[name="emptyStateKeywordSearch"]')
        await search_box.fill('')
        await search_box.fill(job_id)
        await search_box.press('Enter')
        await page.wait_for_timeout(2000)
        
        print(f"Searching for job ID: {job_id}")
        try:
            await apply(page, job_id, resume_path=resume_path, cover_path=cover_path)
        except Exception as e:
            print(f"Error during apply for {job_id}: {e}. Recovering and continuing...")
        # Ensure we have an open page for next iteration
        try:
            if page.is_closed():
                page = await context.new_page()
                await page.goto(START_URL)
                await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=60000)
                await page.wait_for_load_state('networkidle')
        except Exception:
            pass

async def apply(page, job_id, resume_path: str | None = None, cover_path: str | None = None):
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

            # Check for Pre-Screening Questions step; if present, cancel and move to next job id
            try:
                await app_page.wait_for_timeout(300)
                prescreen_frame = None
                # Search frames for the pre-screen container
                for frame in app_page.frames:
                    try:
                        if await frame.locator('#preScreenQuestions').count() > 0:
                            prescreen_frame = frame
                            break
                    except Exception:
                        continue
                # Fallback to page context
                if prescreen_frame is None and await app_page.locator('#preScreenQuestions').count() > 0:
                    prescreen_frame = app_page
                if prescreen_frame is not None:
                    print(f"Row {i+1}: Pre-screening questions detected. Cancelling application for job {job_id}")
                    cancel_btn = prescreen_frame.locator('button.js--ui-wizard-cancel-btn:has-text("Cancel"), button.js--ui-wizard-cancel-btn').first
                    if await cancel_btn.count() > 0:
                        await cancel_btn.click()
                        # Attempt to confirm the cancellation if a modal appears
                        try:
                            # Wait briefly for modal to appear
                            try:
                                await app_page.wait_for_selector('.modal__inner', timeout=2000)
                            except Exception:
                                pass

                            # Prefer the explicit Yes selector when available
                            yes_btn = app_page.locator('button.js--confirm.sel_YesButtonTest, button.sel_YesButtonTest, .modal__inner button.js--confirm:has-text("Yes")').first
                            if await yes_btn.count() == 0:
                                # Fallback to common label-based buttons
                                yes_btn = app_page.locator('button:has-text("Yes"), button:has-text("Confirm"), button:has-text("OK")').first

                            if await yes_btn.count() == 0:
                                # Search within frames as a last resort
                                for frame in app_page.frames:
                                    try:
                                        candidate = frame.locator('button.js--confirm.sel_YesButtonTest, button.sel_YesButtonTest, .modal__inner button.js--confirm:has-text("Yes"), button:has-text("Yes"), button:has-text("Confirm"), button:has-text("OK")').first
                                        if await candidate.count() > 0:
                                            yes_btn = candidate
                                            break
                                    except Exception:
                                        continue

                            if await yes_btn.count() > 0:
                                await yes_btn.click()
                        except Exception:
                            pass
                        # Allow UI to update; safe even if page closed
                        try:
                            await app_page.wait_for_timeout(300)
                        except Exception:
                            pass
                        if app_page.is_closed():
                            app_page = page
                        # Navigate back to job postings for next id
                        try:
                            await app_page.goto(START_URL)
                            await app_page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=60000)
                            await app_page.wait_for_load_state('networkidle')
                        except Exception:
                            pass
                        return
            except Exception:
                pass

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

            # Click "Upload New Résumé" button (target the resume-specific button only)
            upload_button = frame_or_page.locator('button.js--btn--upload-new-doc[data-dt-name="Résumé"]').first
            if await upload_button.count() > 0 and resume_path:
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
                file_path = resume_path
                print(f"Row {i+1}: Setting file input: {file_path}")
                await file_input.set_input_files(file_path)
                # Submit the upload dialog
                submit_upload = frame_or_page.locator('#submitFileUploadFormBtn, button#submitFileUploadFormBtn, button:has-text("Upload A Document")').first
                if await submit_upload.count() > 0:
                    print(f"Row {i+1}: Clicking Upload A Document")
                    await submit_upload.click()
                    await frame_or_page.wait_for_load_state('networkidle')
            elif await upload_button.count() > 0 and not resume_path:
                print(f"Row {i+1}: Skipping Resume upload for job {job_id} (file not found)")

            # If a cover letter upload button exists, click it next
            cover_letter_btn = frame_or_page.locator('button.js--btn--upload-new-doc[data-dt-name="Cover Letter"]').first
            if await cover_letter_btn.count() > 0 and cover_path:
                print(f"Row {i+1}: Clicking Upload New Cover Letter")
                await cover_letter_btn.click()
                # Fill the cover letter document name
                cl_doc_name = frame_or_page.locator('input[name="docName"]').first
                await cl_doc_name.wait_for(state='visible', timeout=20000)
                await cl_doc_name.fill(f"Cover letter + {job_id}")
                await frame_or_page.wait_for_timeout(300)
                # Click the file upload button for cover letter
                cl_file_upload_btn = frame_or_page.locator('#btn_fileUploadDialog_docUpload').first
                if await cl_file_upload_btn.count() > 0:
                    print(f"Row {i+1}: Clicking Cover Letter file upload button")
                    await cl_file_upload_btn.click()
                    await frame_or_page.wait_for_timeout(300)
                    # Set the cover letter file and submit
                    cl_file_input = frame_or_page.locator('input#fileUpload_docUpload, input[type="file"]').first
                    cl_file_path = cover_path
                    print(f"Row {i+1}: Setting cover letter file: {cl_file_path}")
                    await cl_file_input.set_input_files(cl_file_path)
                    cl_submit = frame_or_page.locator('#submitFileUploadFormBtn, button#submitFileUploadFormBtn, button:has-text("Upload A Document")').first
                    if await cl_submit.count() > 0:
                        print(f"Row {i+1}: Submitting Cover Letter upload")
                        await cl_submit.click()
                        await frame_or_page.wait_for_load_state('networkidle')
            elif await cover_letter_btn.count() > 0 and not cover_path:
                print(f"Row {i+1}: Skipping Cover Letter upload for job {job_id} (file not found)")

            # Click the final Submit button to proceed
            submit_btn = frame_or_page.locator('button.js--ui-wizard-next-btn:has-text("Submit"), #button_573121027768999').first
            if await submit_btn.count() > 0:
                print(f"Row {i+1}: Clicking final Submit")
                await submit_btn.click()
                await frame_or_page.wait_for_load_state('networkidle')

            # Click Done to finish the wizard
            done_btn = frame_or_page.locator('button.js--ui-wizard-finish-btn:has-text("Done"), #button_5190379572824657').first
            if await done_btn.count() > 0:
                print(f"Row {i+1}: Clicking Done")
                await done_btn.click()
                await frame_or_page.wait_for_load_state('networkidle')
            
            # Return to Full-Cycle Service, then back to Job Postings for the next job id
            # If the application opened in a new tab, it may be closed after finishing. Fallback to the original page.
            if app_page.is_closed():
                app_page = page
            full_cycle_link = app_page.locator('a[href="/myAccount/co-op/full.htm"], a:has-text("Full-Cycle Service")').first
            if await full_cycle_link.count() > 0:
                print(f"Row {i+1}: Navigating back to Full-Cycle Service")
                await full_cycle_link.click()
                await app_page.wait_for_load_state('networkidle')
            else:
                await app_page.goto('https://waterlooworks.uwaterloo.ca/myAccount/co-op/full.htm')
                await app_page.wait_for_load_state('networkidle')

            # Ensure we are back on the jobs search page for the next iteration
            await app_page.goto(START_URL)
            await app_page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=60000)
            await app_page.wait_for_load_state('networkidle')

async def upload_for_jobs(job_ids: list[str], out_dir: str | None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        # Reuse saved auth state if available
        if os.path.exists(STORAGE_STATE_FILE):
            context = await browser.new_context(storage_state=STORAGE_STATE_FILE)
        else:
            context = await browser.new_context()
        await search_job_by_id(job_ids, context, out_dir=out_dir)
        # Persist any updated session state for future runs
        try:
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            await context.storage_state(path=STORAGE_STATE_FILE)
        except Exception:
            pass
        await browser.close()

if __name__ == "__main__":
    # Example manual run
    asyncio.run(upload_for_jobs(["436892", "436734"], out_dir=None))