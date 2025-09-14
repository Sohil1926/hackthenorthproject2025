import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup, NavigableString
import json
import re
import os
import traceback

# ==============================================================================
# --- CONFIGURATION ---
# ==============================================================================
# URLs and File Paths
START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"]

# Route generated artifacts to a central outputs/ directory at repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUTS_DIR, "waterlooworks_jobs.json")
STORAGE_STATE_FILE = os.path.join(OUTPUTS_DIR, "storage_state.json")

# Scraping Behavior
ACTION_TIMEOUT = 60000  # Increased to 60 seconds for potentially slower connections/renders
RETRY_ATTEMPTS = 2      # How many times to retry scraping a single job's details
# ==============================================================================


def save_data_incrementally(data, filename):
    """Saves the collected data to a JSON file."""
    try:
        # Ensure directory exists for the target file
        dirpath = os.path.dirname(os.path.abspath(filename))
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Progress saved. {len(data)} jobs collected so far in '{filename}'")
    except Exception as e:
        print(f"❌ Error saving data: {e}")


async def get_job_summaries_from_page_full(page):
    """
    Gets a list of job summaries from the current page for the Full/Cycle postings layout.
    """
    print("  Extracting job summaries from the current page (full)...")
    job_summaries = []
    
    try:
        list_selector = "tbody tr.table__row--body"
        await page.wait_for_selector(list_selector, timeout=ACTION_TIMEOUT)
        
        rows = await page.locator(list_selector).all()
        
        for row in rows:
            try:
                # Determine whether the row uses a header (th) for job ID
                th_cells = row.locator("th")
                th_count = await th_cells.count()

                cells = row.locator("td")
                cell_count = await cells.count()
                
                # Ensure we have enough cells before accessing them
                if cell_count < 8:
                    print(f"  Warning: Row has only {cell_count} cells, skipping...")
                    continue

                # Extract job ID and compute the correct index for the job title column
                if th_count >= 1:
                    th_text = await th_cells.nth(0).inner_text(timeout=ACTION_TIMEOUT)
                    numbers = re.findall(r"\d+", th_text)
                    job_id = numbers[-1] if numbers else th_text.strip()
                    title_td_index = 0
                else:
                    job_id = await cells.nth(0).inner_text(timeout=ACTION_TIMEOUT)
                    title_td_index = 1

                job_title_element = cells.nth(title_td_index).locator("a").first
                
                # Check if the job title link exists
                if await job_title_element.count() == 0:
                    print(f"  Warning: No job title link found for job ID {job_id}, skipping...")
                    continue
                
                job_title = await job_title_element.inner_text(timeout=ACTION_TIMEOUT)
                company = await cells.nth(2).inner_text(timeout=ACTION_TIMEOUT)
                division = await cells.nth(3).inner_text(timeout=ACTION_TIMEOUT)
                openings = await cells.nth(4).inner_text(timeout=ACTION_TIMEOUT)
                city = await cells.nth(5).inner_text(timeout=ACTION_TIMEOUT)
                level = await cells.nth(6).inner_text(timeout=ACTION_TIMEOUT)
                deadline = await cells.nth(7).inner_text(timeout=ACTION_TIMEOUT)
                
                job_summaries.append({
                    "id": job_id.strip(),
                    "title": job_title.strip(),
                    "company": company.strip(),
                    "division": division.strip(),
                    "openings": openings.strip(),
                    "city": city.strip(),
                    "level": level.strip(),
                    "deadline": deadline.strip(),
                    "link_locator": job_title_element
                })
            except Exception as e:
                print(f"  Warning: Could not parse a row. Error: {e}")
                continue
                
    except Exception as e:
        print(f"  Error getting job summaries: {e}")
        
    print(f"  Found {len(job_summaries)} jobs on this page (full).")
    return job_summaries


async def get_job_summaries_from_page_direct(page):
    """
    Gets a list of job summaries from the current page for the Direct postings layout.
    """
    print("  Extracting job summaries from the current page (direct)...")
    job_summaries = []
    
    try:
        list_selector = "tbody tr.table__row--body"
        await page.wait_for_selector(list_selector, timeout=ACTION_TIMEOUT)
        
        rows = await page.locator(list_selector).all()
        
        for row in rows:
            try:
                cells = row.locator("td")
                cell_count = await cells.count()
                
                # Ensure we have enough cells before accessing them
                if cell_count < 8:
                    print(f"  Warning: Row has only {cell_count} cells, skipping...")
                    continue
                
                job_id = await cells.nth(0).inner_text(timeout=ACTION_TIMEOUT)
                job_title_element = cells.nth(1).locator("a").first
                
                # Check if the job title link exists
                if await job_title_element.count() == 0:
                    print(f"  Warning: No job title link found for job ID {job_id}, skipping...")
                    continue
                
                job_title = await job_title_element.inner_text(timeout=ACTION_TIMEOUT)
                company = await cells.nth(2).inner_text(timeout=ACTION_TIMEOUT)
                division = await cells.nth(3).inner_text(timeout=ACTION_TIMEOUT)
                openings = await cells.nth(4).inner_text(timeout=ACTION_TIMEOUT)
                city = await cells.nth(5).inner_text(timeout=ACTION_TIMEOUT)
                level = await cells.nth(6).inner_text(timeout=ACTION_TIMEOUT)
                deadline = await cells.nth(7).inner_text(timeout=ACTION_TIMEOUT)
                
                job_summaries.append({
                    "id": job_id.strip(),
                    "title": job_title.strip(),
                    "company": company.strip(),
                    "division": division.strip(),
                    "openings": openings.strip(),
                    "city": city.strip(),
                    "level": level.strip(),
                    "deadline": deadline.strip(),
                    "link_locator": job_title_element
                })
            except Exception as e:
                print(f"  Warning: Could not parse a row. Error: {e}")
                continue
                
    except Exception as e:
        print(f"  Error getting job summaries: {e}")
        
    print(f"  Found {len(job_summaries)} jobs on this page (direct).")
    return job_summaries


async def get_job_summaries_from_page(page):
    """Dispatches to the appropriate parser based on current URL."""
    try:
        current_url = page.url
        if "/myAccount/co-op/direct/jobs.htm" in current_url:
            return await get_job_summaries_from_page_direct(page)
        # Default to full layout otherwise
        return await get_job_summaries_from_page_full(page)
    except Exception:
        # Fallback to full parser
        return await get_job_summaries_from_page_full(page)


async def scrape_job_details(page):
    """
    Scrapes all detailed information from the job detail modal.
    """
    print("    Scraping job details from the modal...")
    
    try:
        modal_selector = "div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)"
        modal_locator = page.locator(modal_selector)
        
        await modal_locator.wait_for(state='visible', timeout=ACTION_TIMEOUT)
        
        # Wait for content to load
        await page.wait_for_load_state("networkidle", timeout=ACTION_TIMEOUT)
        await asyncio.sleep(0.5)  # Small delay to ensure content is rendered
        
        modal_html = await modal_locator.inner_html(timeout=ACTION_TIMEOUT)
        soup = BeautifulSoup(modal_html, 'html.parser')
        
        details = {}
        
        # Extract header info
        header = soup.find('div', class_='dashboard-header--mini')
        if header:
            title_tag = header.find('h2')
            details['job_title'] = title_tag.get_text(strip=True) if title_tag else 'N/A'
            company_info = header.find('div', class_='font--14')
            if company_info:
                spans = company_info.find_all('span')
                if len(spans) >= 2:
                    details['organization'] = spans[0].get_text(strip=True)
                    details['division'] = spans[1].get_text(strip=True) if len(spans) > 1 else 'N/A'

        # Scrape the status tags at the top of the modal
        status_tags = []
        tag_rail = soup.find('div', class_='tag-rail')
        if tag_rail:
            tags = tag_rail.find_all('span', class_='tag-label')
            for tag in tags:
                status_tags.append(tag.get_text(strip=True))
        details['status_tags'] = status_tags

        # Process all sections
        all_section_anchors = soup.find_all('div', class_='tag__key-value-list')
        
        for section in all_section_anchors:
            key_tag = section.find('span', class_='label')
            if not key_tag:
                continue
                
            key = key_tag.get_text(strip=True).replace(':', '').lower().replace(' ', '_').replace('/', '_')
            
            content_parts = []
            
            # Get content from inside the anchor tag itself
            initial_p = section.find('p')
            if initial_p:
                if key == 'level':
                    levels = [td.get_text(strip=True) for td in initial_p.find_all('td')]
                    content_parts.append(', '.join(levels) if levels else 'N/A')
                elif key == 'targeted_degrees_and_disciplines':
                    disciplines = [li.get_text(strip=True) for li in initial_p.find_all('li')]
                    content_parts.append('\n'.join(disciplines) if disciplines else 'N/A')
                elif key == 'additional_information':
                    items = [td.get_text(strip=True) for td in initial_p.find_all('td') if td.get_text(strip=True)]
                    content_parts.append('\n'.join(items) if items else 'N/A')
                else:
                    initial_text = initial_p.get_text(strip=True, separator='\n')
                    if initial_text:
                        content_parts.append(initial_text)

            # Look for subsequent sibling tags until the next section starts
            current = section
            while True:
                current = current.find_next_sibling()
                if current is None:
                    break
                if current.name == 'div' and 'tag__key-value-list' in current.get('class', []):
                    break
                if current.name in ['p', 'ul', 'div'] and not isinstance(current, NavigableString):
                    text = current.get_text(strip=True, separator='\n')
                    if text:
                        content_parts.append(text)
            
            full_content = '\n\n'.join(part for part in content_parts if part and part.strip())
            
            if key != 'job_title':
                details[key] = full_content if full_content else 'N/A'

        return details
        
    except Exception as e:
        print(f"    Error scraping job details: {e}")
        return {"error": str(e)}


async def close_modal_safely(page):
    """Safely close the modal if it's open."""
    try:
        modal_locator = page.locator('div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)')
        if await modal_locator.is_visible(timeout=2000):
            print("    Closing modal...")
            close_button = modal_locator.locator('nav.floating--action-bar button:has(i:text-is("close"))')
            if await close_button.count() > 0:
                await close_button.click()
                await modal_locator.wait_for(state='hidden', timeout=ACTION_TIMEOUT)
                print("    Modal closed.")
            else:
                # Fallback: try ESC key
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"    Warning: Could not close modal. Error: {e}")


async def main(max_jobs: int = None):
    """Launches a browser, waits for user login, then scrapes all jobs and their details."""
    if max_jobs is not None:
        print(f"Scraping limited to {max_jobs} jobs maximum.")
    else:
        print("Scraping all available jobs (unlimited).")
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        # Reuse storage state if available to avoid re-login
        if os.path.exists(STORAGE_STATE_FILE):
            context = await browser.new_context(storage_state=STORAGE_STATE_FILE)
        else:
            context = await browser.new_context()
        page = await context.new_page()

        all_jobs_data = []
        already_scraped_ids = set()
        
        # Resume from previous scrape if file exists
        if os.path.exists(OUTPUT_FILE):
            print(f"Found existing output file '{OUTPUT_FILE}'. Loading it to resume scrape.")
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    all_jobs_data = json.load(f)
                    # Only skip jobs that were scraped successfully (no error key)
                    already_scraped_ids = {
                        job['id'] for job in all_jobs_data 
                        if 'details' in job and isinstance(job['details'], dict) and 'error' not in job['details']
                    }
                    print(f"Resuming. Already scraped {len(already_scraped_ids)} job details successfully.")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load output file. Starting from scratch. Error: {e}")
                all_jobs_data = []

        try:
            await page.goto(START_URL)
            print("\n" + "="*60)
            print("Please log in manually. After login, the script will automatically")
            print("navigate to the job postings page.")
            print("="*60 + "\n")

            # Wait until we're logged in (any myAccount page indicates successful login)
            await page.wait_for_url(lambda url: "/myAccount/" in url, timeout=300000)
            print("✅ Login detected! Navigating to job postings page...")
            
            # Navigate to the job postings page
            job_postings_url = "https://waterlooworks.uwaterloo.ca/myAccount/co-op/full/jobs.htm"
            await page.goto(job_postings_url)
            await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=ACTION_TIMEOUT)
            
            print(f"\n✅ Target page detected ({page.url})! Starting scrape...\n")
            # Persist authenticated session for reuse by other modules
            try:
                await context.storage_state(path=STORAGE_STATE_FILE)
                print(f"Saved session storage state to '{STORAGE_STATE_FILE}'")
            except Exception:
                pass
            
            page_num = 1
            consecutive_failures = 0
            max_consecutive_failures = 5
            
            while True:
                print(f"\n--- Processing Page {page_num} ---")
                
                try:
                    job_summaries_on_page = await get_job_summaries_from_page(page)
                    
                    if not job_summaries_on_page:
                        print("No jobs found on this page, ending process.")
                        break

                    consecutive_failures = 0  # Reset failure counter on successful page load
                    
                    for i, job_summary in enumerate(job_summaries_on_page):
                        if job_summary['id'] in already_scraped_ids:
                            print(f"  -> Skipping job {i+1}/{len(job_summaries_on_page)} (ID: {job_summary['id']}) - Already scraped.")
                            continue

                        print(f"  -> Processing job {i+1}/{len(job_summaries_on_page)} (ID: {job_summary['id']})")
                        
                        job_details = None
                        for attempt in range(RETRY_ATTEMPTS):
                            try:
                                # Close any open modal first
                                await close_modal_safely(page)
                                
                                # Click the job link
                                await job_summary['link_locator'].click()
                                
                                # Scrape details
                                job_details = await scrape_job_details(page)
                                
                                if 'error' not in job_details:
                                    job_summary['details'] = job_details
                                    break
                                else:
                                    raise Exception(job_details['error'])
                                    
                            except Exception as e:
                                print(f"    Attempt {attempt + 1} FAILED. Error: {e}")
                                if attempt < RETRY_ATTEMPTS - 1:
                                    print("    Retrying...")
                                    await close_modal_safely(page)
                                    await asyncio.sleep(2)
                                else:
                                    print(f"    All {RETRY_ATTEMPTS} attempts failed for Job ID {job_summary['id']}.")
                                    job_summary['details'] = {"error": str(e)}
                        
                        # Always try to close modal after processing
                        await close_modal_safely(page)
                        
                        # Remove the link_locator before saving
                        if 'link_locator' in job_summary:
                            del job_summary['link_locator']
                        
                        all_jobs_data.append(job_summary)
                        
                        # Check if we've reached the max_jobs limit
                        if max_jobs is not None and len(all_jobs_data) >= max_jobs:
                            print(f"\n✅ Reached maximum job limit of {max_jobs}. Stopping scrape.")
                            save_data_incrementally(all_jobs_data, OUTPUT_FILE)
                            await browser.close()
                            return
                        
                        # Save progress every 10 jobs
                        if len(all_jobs_data) % 10 == 0:
                            save_data_incrementally(all_jobs_data, OUTPUT_FILE)

                    # Save after each page
                    save_data_incrementally(all_jobs_data, OUTPUT_FILE)

                    # Check for next page
                    next_button = page.locator('a[aria-label="Go to next page"]')
                    next_button_count = await next_button.count()
                    
                    if next_button_count > 0:
                        # Check if button is disabled
                        button_class = await next_button.get_attribute('class') or ''
                        is_disabled = 'disabled' in button_class
                        
                        if not is_disabled:
                            print("\nNavigating to the next page...")
                            
                            # Get current first job ID for comparison
                            first_job_element = page.locator("tbody tr.table__row--body").first.locator("td").first
                            first_job_id_before = await first_job_element.inner_text(timeout=ACTION_TIMEOUT)
                            
                            # Click next button
                            await next_button.click()
                            
                            # Wait for page content to change
                            print("  Waiting for page content to update...")
                            try:
                                await page.wait_for_function(
                                    f'document.querySelector("tbody tr.table__row--body td")?.innerText !== "{first_job_id_before}"',
                                    timeout=ACTION_TIMEOUT
                                )
                                print("  Page content updated.")
                                page_num += 1
                            except:
                                print("  Warning: Could not verify page update. Continuing anyway...")
                                await asyncio.sleep(2)
                                page_num += 1
                        else:
                            print("\nNext button is disabled. Last page reached.")
                            break
                    else:
                        print("\nNo next button found. Last page reached.")
                        break
                        
                except Exception as page_error:
                    consecutive_failures += 1
                    print(f"\n❌ Error processing page {page_num}: {page_error}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"Too many consecutive failures ({max_consecutive_failures}). Stopping scrape.")
                        break
                    
                    print(f"Attempting to recover... (Failure {consecutive_failures}/{max_consecutive_failures})")
                    
                    # Try to recover by reloading the page
                    try:
                        await page.reload(wait_until="networkidle", timeout=ACTION_TIMEOUT)
                        await asyncio.sleep(2)
                    except:
                        print("Could not reload page. Ending scrape.")
                        break

        except asyncio.TimeoutError:
            print(f"\n❌ Operation timed out. The page might be slow or you didn't navigate to the jobs page within 5 minutes.")
        except Exception as e:
            print(f"\n❌ A critical error occurred: {e}")
            traceback.print_exc()
        finally:
            if all_jobs_data:
                save_data_incrementally(all_jobs_data, OUTPUT_FILE)
                print(f"\n{'='*60}")
                print(f"Final Summary: Successfully scraped {len(all_jobs_data)} total jobs.")
                successful_jobs = len([j for j in all_jobs_data if 'details' in j and 'error' not in j.get('details', {})])
                failed_jobs = len(all_jobs_data) - successful_jobs
                print(f"  - Successful: {successful_jobs}")
                print(f"  - Failed: {failed_jobs}")
                print(f"{'='*60}")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


# Convenience wrapper for orchestration
def scrape_jobs(max_jobs: int = None) -> str:
    """
    Runs the interactive scraper and returns the absolute path to the produced
    jobs JSON file. Ensures the scraper runs with the backend directory as the
    working directory so the output lands in `outputs/waterlooworks_jobs.json`.
    
    Args:
        max_jobs: Maximum number of jobs to scrape. If None, scrapes all available jobs.
    """
    backend_dir = os.path.dirname(__file__)
    prev_cwd = os.getcwd()
    try:
        os.chdir(backend_dir)
        asyncio.run(main(max_jobs=max_jobs))
        return OUTPUT_FILE
    finally:
        os.chdir(prev_cwd)