# (Not doing it like this anymore)
# start chrome --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-dev-session"

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# --- Configuration ---
TARGET_URL_FRAGMENT = "/myAccount/co-op/full/jobs.htm"
START_URL = "https://waterlooworks.uwaterloo.ca/home.htm"
BASE_URL = "https://waterlooworks.uwaterloo.ca"

# --- Scraping Functions (Unchanged) ---
# ... (The scrape_job_listings_page and scrape_job_details functions are the same)
async def scrape_job_listings_page(page):
    print("Extracting job listings from the current page...")
    job_listings = []
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # TODO: Inspect the actual webpage to find the correct selectors!
    # Open browser dev tools (F12) → Elements tab → find the job listings table
    # Look for the actual ID or class name used

    # Method 1: Try the expected ID first
    table = soup.find('table', id='postingsTable')

    # Method 2: If that fails, try alternative selectors
    if not table:
        print("postingsTable ID not found, trying alternatives...")
        # Try other common patterns
        table = soup.find('table', class_='postings-table')  # class instead of ID
        if not table:
            table = soup.find('table', {'data-testid': 'postingsTable'})  # data attribute
        if not table:
            # Try finding any table that looks like job listings
            tables = soup.find_all('table')
            for t in tables:
                if t.tbody and len(t.tbody.find_all('tr')) > 5:  # Has multiple rows
                    
                    table = t
                    print(f"Found table with {len(t.tbody.find_all('tr'))} rows")
                    
                    break

    if not table or not table.tbody:
        print("Could not find a valid job postings table on the page.")
        print("This is expected if no jobs are currently available for your account.")
        print("\nDEBUG: Available table IDs and classes:")
        for t in soup.find_all('table'):
            print(f"  Table: id='{t.get('id')}' class='{t.get('class')}'")
        return []
    # --- END OF NEW CHECK ---

    for row in table.tbody.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) > 4:
            job_id = cells[0].get_text(strip=True)
            job_title = cells[1].get_text(strip=True)
            company = cells[2].get_text(strip=True)
            link_tag = cells[1].find('a')
            if link_tag and link_tag.has_attr('href'):
                relative_link = link_tag['href']
                full_link = f"{BASE_URL}{relative_link}"
                job_listings.append({
                    "id": job_id,
                    "title": job_title,
                    "company": company,
                    "link": full_link
                })
    print(f"Found {len(job_listings)} jobs on this page.")
    return job_listings

async def scrape_job_details(context, job_link):
    print(f"Scraping details for: {job_link}")
    new_page = await context.new_page()
    try:
        await new_page.goto(job_link)
        await new_page.wait_for_selector(".panel-body", timeout=15000)
        html = await new_page.content()
        soup = BeautifulSoup(html, 'html.parser')
        details = {}
        def get_detail_text(label):
            element = soup.find('strong', string=lambda text: text and label.lower() in text.lower())
            if element and element.parent and element.parent.next_sibling:
                return element.parent.next_sibling.get_text(strip=True)
            return "Not Found"
        details['job_title'] = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Not Found"
        details['company'] = get_detail_text('Company:')
        details['location'] = get_detail_text('Location:')
        details['job_summary'] = get_detail_text('Job Summary:')
        details['responsibilities'] = get_detail_text('Job Responsibilities:')
        details['required_skills'] = get_detail_text('Required Skills:')
        return details
    finally:
        await new_page.close()

# --- Main Function (Unchanged) ---
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(START_URL)

        print("\n" + "="*60)
        print("A browser window has been opened.")
        print("Please log in and navigate to the co-op job postings page.")
        print("The script will automatically continue once you arrive.")
        print("="*60 + "\n")

        try:
            await page.wait_for_url(f"**{TARGET_URL_FRAGMENT}", timeout=300000)
            print("\n✅ Job postings page detected! Starting the scrape...\n")
            
            jobs_on_page = await scrape_job_listings_page(page)

            if not jobs_on_page:
                print("\nNo jobs were found on the page. Exiting.")
            else:
                print("\n--- Scraping Details for a Sample of Jobs ---")
                for job in jobs_on_page[:3]:
                    job_details = await scrape_job_details(context, job['link'])
                    print("\n-------------------------------------------")
                    if job_details:
                        print(f"Job Title: {job_details.get('job_title', 'Not Found')}")
                        print(f"Company: {job_details.get('company', 'Not Found')}")
                    else:
                        print("Failed to scrape job details")
                    # ... and so on
                    print("-------------------------------------------\n")

        except asyncio.TimeoutError:
            print("\n❌ Timed out waiting for you to navigate to the job postings page.")
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
        finally:
            print("Script finished. Closing the browser.")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())