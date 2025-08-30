import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re
import time

# ==============================================================================
# --- CONFIGURATION ---
# ==============================================================================
# URLs and File Paths
START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"]
OUTPUT_FILE = "waterlooworks_jobs.json"

# Scraping Behavior
ACTION_TIMEOUT = 10000  # 10 seconds for critical waits
RETRY_ATTEMPTS = 2      # How many times to retry scraping a single job's details
# ==============================================================================


def save_data_incrementally(data, filename):
    """Saves the collected data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Progress saved. {len(data)} jobs collected so far in '{filename}'")


async def get_job_summaries_from_page(page):
    """
    Gets a list of job summaries from the current page.
    Each summary includes the title and a Playwright locator for its link.
    """
    print("  Extracting job summaries from the current page...")
    job_summaries = []
    
    list_selector = "tbody tr.table__row--body"
    await page.wait_for_selector(list_selector, timeout=ACTION_TIMEOUT)
    
    rows = await page.locator(list_selector).all()
    
    for row in rows:
        try:
            job_id = await row.locator("td").nth(0).inner_text(timeout=ACTION_TIMEOUT)
            job_title_element = row.locator("td").nth(1).locator("a")
            job_title = await job_title_element.inner_text(timeout=ACTION_TIMEOUT)
            company = await row.locator("td").nth(2).inner_text(timeout=ACTION_TIMEOUT)
            
            job_summaries.append({
                "id": job_id.strip(),
                "title": job_title.strip(),
                "company": company.strip(),
                "link_locator": job_title_element
            })
        except Exception as e:
            print(f"  Warning: Could not parse a row. Error: {e}")
            
    print(f"  Found {len(job_summaries)} jobs on this page.")
    return job_summaries

async def scrape_job_details(page):
    """
    Scrapes all detailed information from the job detail modal.
    IMPROVED: This version is more generic and robust.
    """
    print("    Scraping job details from the modal...")
    
    modal_selector = "div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)"
    modal_locator = page.locator(modal_selector)
    
    await modal_locator.wait_for(state='visible', timeout=ACTION_TIMEOUT)
    await modal_locator.locator('h4:text-is("Job Posting Information")').wait_for(timeout=ACTION_TIMEOUT)
    
    modal_html = await modal_locator.inner_html(timeout=ACTION_TIMEOUT)
    soup = BeautifulSoup(modal_html, 'html.parser')
    
    details = {}
    
    # Extract header info first
    header = soup.find('div', class_='dashboard-header--mini')
    if header:
        title_tag = header.find('h2')
        details['job_title'] = title_tag.get_text(strip=True) if title_tag else 'N/A'
        
        company_info = header.find('div', class_='font--14')
        if company_info:
            spans = company_info.find_all('span')
            if len(spans) >= 2:
                details['organization'] = spans[0].get_text(strip=True)
                details['division'] = spans[1].get_text(strip=True)

    # --- IMPROVED: Generic Key-Value Pair Extraction ---
    # This loop finds all sections and all key-value pairs within them.
    panels = soup.find_all('div', class_='panel')
    for panel in panels:
        panel_title_tag = panel.find('h4', class_='heading--banner')
        if panel_title_tag:
            panel_title = panel_title_tag.get_text(strip=True)
            
            # Extract all key-value pairs within this panel
            key_value_pairs = panel.find_all('div', class_='tag__key-value-list')
            for pair in key_value_pairs:
                key_tag = pair.find('span', class_='label')
                if not key_tag:
                    continue
                
                key = key_tag.get_text(strip=True).replace(':', '').lower().replace(' ', '_').replace('/', '_')
                
                value_tag = pair.find('p')
                if value_tag:
                    # Handle special cases with nested tables or lists
                    if key == 'level':
                        levels = [td.get_text(strip=True) for td in value_tag.find_all('td')]
                        value = ', '.join(levels) if levels else 'N/A'
                    elif key == 'targeted_degrees_and_disciplines':
                        disciplines = [li.get_text(strip=True) for li in value_tag.find_all('li')]
                        value = disciplines if disciplines else 'N/A'
                    elif key == 'additional_information':
                        items = [td.get_text(strip=True) for td in value_tag.find_all('td') if td.get_text(strip=True)]
                        value = items if items else 'N/A'
                    else:
                        # General case: get all text, preserving line breaks for descriptions
                        value = value_tag.get_text(strip=True, separator='\n')
                else:
                    value = 'N/A'
                
                # Add to details dictionary, avoiding overwriting the main job title
                if key != 'job_title':
                    details[key] = value

    return details


async def main():
    """Launches a browser, waits for user login, then scrapes all jobs and their details."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()

        all_jobs_data = []
        try:
            await page.goto(START_URL)
            print("\n" + "="*60)
            print("Please log in and navigate to a job postings page.")
            print("The script will automatically continue once you arrive.")
            print("="*60 + "\n")

            await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=300000)
            
            print(f"\n✅ Target page detected ({page.url})! Starting scrape...\n")
            
            page_num = 1
            while True:
                print(f"\n--- Processing Page {page_num} ---")
                
                job_summaries_on_page = await get_job_summaries_from_page(page)
                if not job_summaries_on_page:
                    print("No jobs found on this page, ending process.")
                    break

                for i, job_summary in enumerate(job_summaries_on_page):
                    print(f"  -> Processing job {i+1}/{len(job_summaries_on_page)} (ID: {job_summary['id']})")
                    
                    job_details = None
                    # --- IMPROVED: Retry Mechanism ---
                    for attempt in range(RETRY_ATTEMPTS):
                        try:
                            await job_summary['link_locator'].click()
                            job_details = await scrape_job_details(page)
                            job_summary['details'] = job_details
                            break # Success, exit retry loop
                        except Exception as e:
                            print(f"    Attempt {attempt + 1} FAILED. Error: {e}")
                            if attempt < RETRY_ATTEMPTS - 1:
                                print("    Retrying...")
                                # Ensure modal is closed before retrying
                                modal_locator = page.locator('div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)')
                                if await modal_locator.is_visible(timeout=2000):
                                    await modal_locator.locator('nav.floating--action-bar button:has(i:text-is("close"))').click()
                                    await modal_locator.wait_for(state='hidden', timeout=ACTION_TIMEOUT)
                                await asyncio.sleep(2) # Wait a moment before retrying
                            else:
                                print(f"    All {RETRY_ATTEMPTS} attempts failed for Job ID {job_summary['id']}.")
                                job_summary['details'] = {"error": str(e)}
                    
                    # Always try to close the modal to get back to a clean state
                    try:
                        modal_locator = page.locator('div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)')
                        if await modal_locator.is_visible(timeout=5000):
                            print("    Closing modal...")
                            close_button = modal_locator.locator('nav.floating--action-bar button:has(i:text-is("close"))')
                            await close_button.click()
                            await modal_locator.wait_for(state='hidden', timeout=ACTION_TIMEOUT)
                            print("    Modal closed.")
                    except Exception as close_error:
                        print(f"    Could not close modal gracefully. Forcing page reload to recover. Error: {close_error}")
                        await page.reload(wait_until="networkidle")
                        break # Break inner loop to restart scraping on the reloaded page
                    
                    del job_summary['link_locator'] 
                    all_jobs_data.append(job_summary)

                # --- IMPROVED: Incremental Saving ---
                save_data_incrementally(all_jobs_data, OUTPUT_FILE)

                # Check for pagination
                next_button = page.locator('a[aria-label="Go to next page"]')
                is_disabled = 'disabled' in (await next_button.get_attribute('class') or '')
                
                if await next_button.count() > 0 and not is_disabled:
                    print("\nNavigating to the next page...")
                    first_job_id_before_click = await page.locator("tbody tr.table__row--body").first.locator("td").first.inner_text()
                    await next_button.click()
                    
                    print("  Waiting for page content to update...")
                    await page.wait_for_function(
                        f'document.querySelector("tbody tr.table__row--body td")?.innerText !== "{first_job_id_before_click}"',
                        timeout=ACTION_TIMEOUT
                    )
                    print("  Page content updated.")
                    page_num += 1
                else:
                    print("\nLast page reached. Scraping complete.")
                    break

        except asyncio.TimeoutError:
            print(f"\n❌ Operation timed out after {ACTION_TIMEOUT/1000} seconds. The page might be slow or an element is missing.")
        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            # Final save just in case
            if all_jobs_data:
                save_data_incrementally(all_jobs_data, OUTPUT_FILE)

            print("Script finished. Closing the browser in 10 seconds.")
            await asyncio.sleep(10)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())