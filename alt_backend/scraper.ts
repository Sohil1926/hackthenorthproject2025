//# Option 1: Using ts-node directly
// npx ts-node scraper.ts

//# Option 2: Compile then run
// npm run build
// npm start
// start is currently binded to: "start": "node dist/scraper.js"

// scraper.ts
import { chromium, Page, Locator, Browser, BrowserContext } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { JSDOM } from 'jsdom';

// ==============================================================================
// --- CONFIGURATION ---
// ==============================================================================
const START_URL = "https://waterlooworks.uwaterloo.ca/home.htm";
const URL_FRAGMENTS = ["/myAccount/co-op/full/jobs.htm", "/myAccount/co-op/direct/jobs.htm"];
const OUTPUT_FILE = "waterlooworks_jobs.json";

const ACTION_TIMEOUT = 15000; // 15 seconds for potentially slower connections/renders
const RETRY_ATTEMPTS = 2;     // How many times to retry scraping a single job's details

// ==============================================================================
// --- TYPE DEFINITIONS ---
// ==============================================================================
interface JobSummary {
  id: string;
  title: string;
  company: string;
  division: string;
  openings: string;
  city: string;
  level: string;
  deadline: string;
  link_locator?: Locator;
  details?: JobDetails | { error: string };
}

interface JobDetails {
  job_title?: string;
  organization?: string;
  division?: string;
  status_tags?: string[];
  [key: string]: any; // For dynamic field names
}

// ==============================================================================
// --- HELPER FUNCTIONS ---
// ==============================================================================

function saveDataIncrementally(data: JobSummary[], filename: string): void {
  try {
    fs.writeFileSync(filename, JSON.stringify(data, null, 4), 'utf-8');
    console.log(`\n✅ Progress saved. ${data.length} jobs collected so far in '${filename}'`);
  } catch (error) {
    console.error(`❌ Error saving data: ${error}`);
  }
}

async function getJobSummariesFromPage(page: Page): Promise<JobSummary[]> {
  console.log("  Extracting job summaries from the current page...");
  const jobSummaries: JobSummary[] = [];
  
  try {
    const listSelector = "tbody tr.table__row--body";
    await page.waitForSelector(listSelector, { timeout: ACTION_TIMEOUT });
    
    const rows = await page.locator(listSelector).all();
    
    for (const row of rows) {
      try {
        const cells = row.locator("td");
        const cellCount = await cells.count();
        
        // Ensure we have enough cells before accessing them
        if (cellCount < 8) {
          console.log(`  Warning: Row has only ${cellCount} cells, skipping...`);
          continue;
        }
        
        const jobId = await cells.nth(0).innerText({ timeout: ACTION_TIMEOUT });
        const jobTitleElement = cells.nth(1).locator("a").first();
        
        // Check if the job title link exists
        if (await jobTitleElement.count() === 0) {
          console.log(`  Warning: No job title link found for job ID ${jobId}, skipping...`);
          continue;
        }
        
        const jobTitle = await jobTitleElement.innerText({ timeout: ACTION_TIMEOUT });
        const company = await cells.nth(2).innerText({ timeout: ACTION_TIMEOUT });
        const division = await cells.nth(3).innerText({ timeout: ACTION_TIMEOUT });
        const openings = await cells.nth(4).innerText({ timeout: ACTION_TIMEOUT });
        const city = await cells.nth(5).innerText({ timeout: ACTION_TIMEOUT });
        const level = await cells.nth(6).innerText({ timeout: ACTION_TIMEOUT });
        const deadline = await cells.nth(7).innerText({ timeout: ACTION_TIMEOUT });
        
        jobSummaries.push({
          id: jobId.trim(),
          title: jobTitle.trim(),
          company: company.trim(),
          division: division.trim(),
          openings: openings.trim(),
          city: city.trim(),
          level: level.trim(),
          deadline: deadline.trim(),
          link_locator: jobTitleElement
        });
      } catch (error) {
        console.log(`  Warning: Could not parse a row. Error: ${error}`);
        continue;
      }
    }
  } catch (error) {
    console.log(`  Error getting job summaries: ${error}`);
  }
  
  console.log(`  Found ${jobSummaries.length} jobs on this page.`);
  return jobSummaries;
}

async function scrapeJobDetails(page: Page): Promise<JobDetails | { error: string }> {
  console.log("    Scraping job details from the modal...");
  
  try {
    const modalSelector = "div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)";
    const modalLocator = page.locator(modalSelector);
    
    await modalLocator.waitFor({ state: 'visible', timeout: ACTION_TIMEOUT });
    
    // Wait for content to load
    await page.waitForLoadState("networkidle", { timeout: ACTION_TIMEOUT });
    await page.waitForTimeout(500); // Small delay to ensure content is rendered
    
    const modalHtml = await modalLocator.innerHTML({ timeout: ACTION_TIMEOUT });
    const dom = new JSDOM(modalHtml);
    const document = dom.window.document;
    
    const details: JobDetails = {};
    
    // Extract header info
    const header = document.querySelector('div.dashboard-header--mini');
    if (header) {
      const titleTag = header.querySelector('h2');
      details.job_title = titleTag?.textContent?.trim() || 'N/A';
      
      const companyInfo = header.querySelector('div.font--14');
      if (companyInfo) {
        const spans = companyInfo.querySelectorAll('span');
        if (spans.length >= 1) {
          details.organization = spans[0]?.textContent?.trim() || 'N/A';
          details.division = spans[1]?.textContent?.trim() || 'N/A';
        }
      }
    }
    
    // Scrape the status tags at the top of the modal
    const statusTags: string[] = [];
    const tagRail = document.querySelector('div.tag-rail');
    if (tagRail) {
      const tags = tagRail.querySelectorAll('span.tag-label');
      tags.forEach(tag => {
        const text = tag.textContent?.trim();
        if (text) statusTags.push(text);
      });
    }
    details.status_tags = statusTags;
    
    // Process all sections
    const allSectionAnchors = document.querySelectorAll('div.tag__key-value-list');
    
    allSectionAnchors.forEach(section => {
      const keyTag = section.querySelector('span.label');
      if (!keyTag) return;
      
      const key = keyTag.textContent?.trim()
        .replace(':', '')
        .toLowerCase()
        .replace(/ /g, '_')
        .replace(/\//g, '_') || '';
      
      const contentParts: string[] = [];
      
      // Get content from inside the anchor tag itself
      const initialP = section.querySelector('p');
      if (initialP) {
        if (key === 'level') {
          const levels = Array.from(initialP.querySelectorAll('td'))
            .map(td => td.textContent?.trim())
            .filter(Boolean);
          contentParts.push(levels.length ? levels.join(', ') : 'N/A');
        } else if (key === 'targeted_degrees_and_disciplines') {
          const disciplines = Array.from(initialP.querySelectorAll('li'))
            .map(li => li.textContent?.trim())
            .filter(Boolean);
          contentParts.push(disciplines.length ? disciplines.join('\n') : 'N/A');
        } else if (key === 'additional_information') {
          const items = Array.from(initialP.querySelectorAll('td'))
            .map(td => td.textContent?.trim())
            .filter(Boolean);
          contentParts.push(items.length ? items.join('\n') : 'N/A');
        } else {
          const initialText = initialP.textContent?.trim();
          if (initialText) {
            contentParts.push(initialText);
          }
        }
      }
      
      // Look for subsequent sibling tags until the next section starts
      let current = section.nextElementSibling;
      while (current) {
        if (current.nodeName === 'DIV' && current.classList.contains('tag__key-value-list')) {
          break;
        }
        if (['P', 'UL', 'DIV'].includes(current.nodeName)) {
          const text = current.textContent?.trim();
          if (text) {
            contentParts.push(text);
          }
        }
        current = current.nextElementSibling;
      }
      
      const fullContent = contentParts
        .filter(part => part && part.trim())
        .join('\n\n');
      
      if (key && key !== 'job_title') {
        details[key] = fullContent || 'N/A';
      }
    });
    
    return details;
    
  } catch (error) {
    console.log(`    Error scraping job details: ${error}`);
    return { error: String(error) };
  }
}

async function closeModalSafely(page: Page): Promise<void> {
  try {
    const modalLocator = page.locator('div.modal__inner--document-overlay:not(#pdfPreviewModal_modalInner)');
    const isVisible = await modalLocator.isVisible({ timeout: 2000 });
    
    if (isVisible) {
      console.log("    Closing modal...");
      const closeButton = modalLocator.locator('nav.floating--action-bar button:has(i:text-is("close"))');
      
      if (await closeButton.count() > 0) {
        await closeButton.click();
        await modalLocator.waitFor({ state: 'hidden', timeout: ACTION_TIMEOUT });
        console.log("    Modal closed.");
      } else {
        // Fallback: try ESC key
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
      }
    }
  } catch (error) {
    console.log(`    Warning: Could not close modal. Error: ${error}`);
  }
}

async function main(): Promise<void> {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 50 
  });
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  let allJobsData: JobSummary[] = [];
  const alreadyScrapedIds = new Set<string>();
  
  // Resume from previous scrape if file exists
  if (fs.existsSync(OUTPUT_FILE)) {
    console.log(`Found existing output file '${OUTPUT_FILE}'. Loading it to resume scrape.`);
    try {
      const fileContent = fs.readFileSync(OUTPUT_FILE, 'utf-8');
      allJobsData = JSON.parse(fileContent);
      
      // Only skip jobs that were scraped successfully (no error key)
      for (const job of allJobsData) {
        if (job.details && typeof job.details === 'object' && !('error' in job.details)) {
          alreadyScrapedIds.add(job.id);
        }
      }
      
      console.log(`Resuming. Already scraped ${alreadyScrapedIds.size} job details successfully.`);
    } catch (error) {
      console.log(`Warning: Could not load output file. Starting from scratch. Error: ${error}`);
      allJobsData = [];
    }
  }
  
  try {
    await page.goto(START_URL);
    console.log("\n" + "=".repeat(60));
    console.log("Please log in and navigate to a job postings page.");
    console.log("The script will automatically continue once you arrive.");
    console.log("=".repeat(60) + "\n");
    
    await page.waitForURL(
      (url) => URL_FRAGMENTS.some(fragment => url.href.includes(fragment)),
      { timeout: 300000 }
    );
    
    console.log(`\n✅ Target page detected (${page.url()})! Starting scrape...\n`);
    
    let pageNum = 1;
    let consecutiveFailures = 0;
    const maxConsecutiveFailures = 5;
    
    while (true) {
      console.log(`\n--- Processing Page ${pageNum} ---`);
      
      try {
        const jobSummariesOnPage = await getJobSummariesFromPage(page);
        
        if (jobSummariesOnPage.length === 0) {
          console.log("No jobs found on this page, ending process.");
          break;
        }
        
        consecutiveFailures = 0; // Reset failure counter on successful page load
        
        for (let i = 0; i < jobSummariesOnPage.length; i++) {
          const jobSummary = jobSummariesOnPage[i];
          
          if (alreadyScrapedIds.has(jobSummary.id)) {
            console.log(`  -> Skipping job ${i+1}/${jobSummariesOnPage.length} (ID: ${jobSummary.id}) - Already scraped.`);
            continue;
          }
          
          console.log(`  -> Processing job ${i+1}/${jobSummariesOnPage.length} (ID: ${jobSummary.id})`);
          
          let jobDetails: JobDetails | { error: string } | undefined;
          
          for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
            try {
              // Close any open modal first
              await closeModalSafely(page);
              
              // Click the job link
              if (jobSummary.link_locator) {
                await jobSummary.link_locator.click();
              }
              
              // Scrape details
              jobDetails = await scrapeJobDetails(page);
              
              if (!('error' in jobDetails)) {
                jobSummary.details = jobDetails;
                break;
              } else {
                throw new Error(jobDetails.error);
              }
            } catch (error) {
              console.log(`    Attempt ${attempt + 1} FAILED. Error: ${error}`);
              if (attempt < RETRY_ATTEMPTS - 1) {
                console.log("    Retrying...");
                await closeModalSafely(page);
                await page.waitForTimeout(2000);
              } else {
                console.log(`    All ${RETRY_ATTEMPTS} attempts failed for Job ID ${jobSummary.id}.`);
                jobSummary.details = { error: String(error) };
              }
            }
          }
          
          // Always try to close modal after processing
          await closeModalSafely(page);
          
          // Remove the link_locator before saving
          delete jobSummary.link_locator;
          
          allJobsData.push(jobSummary);
          
          // Save progress every 10 jobs
          if (allJobsData.length % 10 === 0) {
            saveDataIncrementally(allJobsData, OUTPUT_FILE);
          }
        }
        
        // Save after each page
        saveDataIncrementally(allJobsData, OUTPUT_FILE);
        
        // Check for next page
        const nextButton = page.locator('a[aria-label="Go to next page"]');
        const nextButtonCount = await nextButton.count();
        
        if (nextButtonCount > 0) {
          // Check if button is disabled
          const buttonClass = await nextButton.getAttribute('class') || '';
          const isDisabled = buttonClass.includes('disabled');
          
          if (!isDisabled) {
            console.log("\nNavigating to the next page...");
            
            // Get current first job ID for comparison
            const firstJobElement = page.locator("tbody tr.table__row--body").first().locator("td").first();
            const firstJobIdBefore = await firstJobElement.innerText({ timeout: ACTION_TIMEOUT });
            
            // Click next button
            await nextButton.click();
            
            // Wait for page content to change
            console.log("  Waiting for page content to update...");
            try {
              await page.waitForFunction(
                (idBefore) => {
                  const firstCell = document.querySelector("tbody tr.table__row--body td");
                  return firstCell?.textContent !== idBefore;
                },
                firstJobIdBefore,
                { timeout: ACTION_TIMEOUT }
              );
              console.log("  Page content updated.");
              pageNum++;
            } catch {
              console.log("  Warning: Could not verify page update. Continuing anyway...");
              await page.waitForTimeout(2000);
              pageNum++;
            }
          } else {
            console.log("\nNext button is disabled. Last page reached.");
            break;
          }
        } else {
          console.log("\nNo next button found. Last page reached.");
          break;
        }
        
      } catch (pageError) {
        consecutiveFailures++;
        console.log(`\n❌ Error processing page ${pageNum}: ${pageError}`);
        
        if (consecutiveFailures >= maxConsecutiveFailures) {
          console.log(`Too many consecutive failures (${maxConsecutiveFailures}). Stopping scrape.`);
          break;
        }
        
        console.log(`Attempting to recover... (Failure ${consecutiveFailures}/${maxConsecutiveFailures})`);
        
        // Try to recover by reloading the page
        try {
          await page.reload({ waitUntil: "networkidle", timeout: ACTION_TIMEOUT });
          await page.waitForTimeout(2000);
        } catch {
          console.log("Could not reload page. Ending scrape.");
          break;
        }
      }
    }
    
  } catch (error) {
    if (error instanceof Error && error.name === 'TimeoutError') {
      console.log("\n❌ Operation timed out. The page might be slow or you didn't navigate to the jobs page within 5 minutes.");
    } else {
      console.log(`\n❌ A critical error occurred: ${error}`);
      console.trace();
    }
  } finally {
    if (allJobsData.length > 0) {
      saveDataIncrementally(allJobsData, OUTPUT_FILE);
      console.log("\n" + "=".repeat(60));
      console.log(`Final Summary: Successfully scraped ${allJobsData.length} total jobs.`);
      
      const successfulJobs = allJobsData.filter(
        j => j.details && typeof j.details === 'object' && !('error' in j.details)
      ).length;
      const failedJobs = allJobsData.length - successfulJobs;
      
      console.log(`  - Successful: ${successfulJobs}`);
      console.log(`  - Failed: ${failedJobs}`);
      console.log("=".repeat(60));
    }
    
    console.log("\nScript finished. Browser will close...");
    await browser.close();
  }
}

// Run the main function
main().catch(console.error);