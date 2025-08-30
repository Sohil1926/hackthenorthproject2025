import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re

# --- Configuration ---
# Define the target pages. The script will activate on any of them.
URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"]
START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
OUTPUT_FILE = "waterlooworks_jobs.json"

# --- Scraping Functions ---

async def scrape_job_listings_from_page(page):
    """
    Scrapes the currently visible job listings from the main table.
    This function is fast and gathers the identifiers for all jobs on the page.
    """
    print("Extracting job listings from the current page...")
    job_listings = []
    
    # Wait for the table body to be populated with at least one row
    await page.wait_for_selector("tbody tr.table__row--body", timeout=20000)
    
    rows = await page.locator("tbody tr.table__row--body").all()
    
    for row in rows:
        try:
            # Extract data using locators relative to the row for speed and reliability
            job_id = await row.locator("td").nth(0).inner_text()
            job_title_element = row.locator("td").nth(1).locator("a")
            job_title = await job_title_element.inner_text()
            company = await row.locator("td").nth(2).inner_text()
            
            job_listings.append({
                "id": job_id.strip(),
                "title": job_title.strip(),
                "company": company.strip(),
            })
        except Exception as e:
            print(f"Warning: Could not parse a row. It might be a non-standard row. Error: {e}")
            
    print(f"Found {len(job_listings)} jobs on this page.")
    return job_listings

async def scrape_job_details(page):
    """
    Scrapes the detailed information from the job detail modal/overlay.
    This function is specifically tailored to the provided HTML structure.
    """
    print("Scraping job details from the modal...")
    
    modal_selector = "div.modal__inner--document-overlay"
    await page.wait_for_selector(modal_selector, timeout=15000)
    
    modal_html = await page.locator(modal_selector).inner_html()
    soup = BeautifulSoup(modal_html, 'html.parser')
    
    details = {}
    
    # --- Extract Header Info ---
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

    # --- Extract Key-Value Pairs from the main body ---
    key_value_pairs = soup.find_all('div', class_='tag__key-value-list')
    for pair in key_value_pairs:
        key_tag = pair.find('span', class_='label')
        if not key_tag:
            continue
            
        # Clean up the key text
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
            
        details[key] = value

    return details


async def main():
    """Launches a browser, waits for user login, then scrapes all jobs and their details."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(START_URL)

        print("\n" + "="*60)
        print("A browser window has been opened.")
        print("Please log in and navigate to a job postings page.")
        print("The script will automatically continue once you arrive.")
        print("="*60 + "\n")

        all_job_listings = []
        try:
            await page.wait_for_url(lambda url: any(frag in url for frag in URL_FRAGMENTS), timeout=300000)
            
            print(f"\n✅ Target page detected ({page.url})! Starting scrape...\n")
            
            # --- Step 1: Scrape all job listings from all pages first ---
            page_num = 1
            while True:
                print(f"\n--- Scraping Listings Page {page_num} ---")
                
                jobs_on_this_page = await scrape_job_listings_from_page(page)
                if not jobs_on_this_page:
                    print("No more jobs found on this page.")
                    break
                
                all_job_listings.extend(jobs_on_this_page)

                next_button = page.locator('a[aria-label="Go to next page"]')
                is_disabled = 'disabled' in (await next_button.get_attribute('class') or '')
                
                if await next_button.count() > 0 and not is_disabled:
                    print("Navigating to the next page...")
                    await next_button.click()
                    await page.wait_for_load_state('networkidle', timeout=20000)
                    page_num += 1
                else:
                    print("Last page reached.")
                    break

            print(f"\n✅ Finished scraping all listings. Total jobs found: {len(all_job_listings)}")

            # --- Step 2: Go back to the first page to start scraping details ---
            print("\n--- Now scraping details for each job ---")
            if "?" in page.url:
                base_list_url = page.url.split("?")[0]
                await page.goto(base_list_url)
                await page.wait_for_load_state('networkidle')

            # --- Step 3: Iterate through the collected list to get details ---
            for i, job in enumerate(all_job_listings):
                print(f"Processing {i+1}/{len(all_job_listings)}: Job ID {job['id']} - '{job['title']}'")
                
                try:
                    # Use a regular expression for a more robust link search
                    job_link = page.get_by_role("link", name=re.compile(f"^{re.escape(job['title'])}$", re.IGNORECASE), exact=False)
                    
                    # Paginate until the job link is visible
                    current_page_for_detail = 1
                    while await job_link.count() == 0:
                        print(f"  Job not on page {current_page_for_detail}, moving to next...")
                        next_button = page.locator('a[aria-label="Go to next page"]')
                        if await next_button.count() == 0 or 'disabled' in (await next_button.get_attribute('class') or ''):
                            raise Exception("Could not find job link after checking all pages.")
                        await next_button.click()
                        await page.wait_for_load_state('networkidle')
                        current_page_for_detail += 1
                        job_link = page.get_by_role("link", name=re.compile(f"^{re.escape(job['title'])}$", re.IGNORECASE), exact=False)

                    await job_link.first.click()
                    
                    job_details = await scrape_job_details(page)
                    job['details'] = job_details
                    
                    # Close the modal to return to the list
                    close_button = page.locator('div.modal__inner--document-overlay button[aria-label*="Close"]')
                    await close_button.click()
                    
                    # Wait for the modal to fully disappear before proceeding
                    await page.wait_for_selector('div.modal__inner--document-overlay', state='hidden', timeout=15000)

                except Exception as e:
                    print(f"  ❌ FAILED to process details for Job ID {job['id']}. Error: {e}")
                    job['details'] = {"error": str(e)}
                    # Reset state by reloading the page
                    await page.reload()
                    await page.wait_for_load_state('networkidle')

        except asyncio.TimeoutError:
            print("\n❌ Timed out waiting for you to navigate to the correct page.")
        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            if all_job_listings:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_job_listings, f, ensure_ascii=False, indent=4)
                print(f"\n✅ Job data saved to {OUTPUT_FILE}")

            print("Script finished. Closing the browser in 10 seconds.")
            await asyncio.sleep(10)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())