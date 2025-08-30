# integrate.py (Ideal Version 2.0)

import json
import os
from tqdm import tqdm  # For the progress bar

# Import the new JobMatcher class from our ideal matcher.py
from matcher import JobMatcher

# --- Configuration ---
JOBS_INPUT_FILE = "waterlooworks_jobs.json"
RESUME_FILE = "my_resume.pdf"  # <-- IMPORTANT: Make sure this file exists!
OUTPUT_FILE = "jobs_with_scores.json"

def main():
    """
    Main function to load scraped jobs, enrich them with AI-powered match
    analysis, and save the sorted results.
    """
    print("--- Starting Phase 2: AI Integration & Scoring ---")

    # 1. Load the scraped jobs data from the scraper's output
    try:
        with open(JOBS_INPUT_FILE, 'r', encoding='utf-8') as f:
            all_jobs = json.load(f)
        print(f"✅ Successfully loaded {len(all_jobs)} jobs from '{JOBS_INPUT_FILE}'")
    except FileNotFoundError:
        print(f"❌ ERROR: The input file '{JOBS_INPUT_FILE}' was not found.")
        print("-> Please run the scraper.py script first to generate it.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERROR: Could not parse JSON in '{JOBS_INPUT_FILE}'. It might be empty or corrupted.")
        return

    # 2. Initialize the JobMatcher with your resume.
    # This parses the resume once and prepares the matcher for efficient scoring.
    try:
        matcher = JobMatcher(resume_path=RESUME_FILE)
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        print(f"-> Please add your resume as '{RESUME_FILE}' to the project folder.")
        return

    # 3. Iterate through each job, calculate the match analysis, and store it.
    enriched_jobs = []
    
    # The tqdm wrapper creates a beautiful progress bar
    for job in tqdm(all_jobs, desc="🤖 Scoring jobs"):
        # The matcher returns a rich dictionary with score, matched skills, etc.
        match_analysis = matcher.calculate_match(job)
        
        # Create a new dictionary to hold the final, enriched job data
        enriched_job = job.copy()
        enriched_job['match_analysis'] = match_analysis
        enriched_jobs.append(enriched_job)

    # 4. Sort the enriched jobs by score in descending order
    enriched_jobs.sort(key=lambda x: x['match_analysis']['score'], reverse=True)

    # 5. Print a helpful summary of the top 5 matches
    print("\n--- Top 5 Job Matches ---")
    for job in enriched_jobs[:5]:
        analysis = job['match_analysis']
        print(f"\n  - {analysis['score']}%: {job['title']} @ {job['company']}")
        if analysis['matched_skills']:
            print(f"    ✅ Matched Skills: {', '.join(analysis['matched_skills'])}")
        if analysis['missing_skills']:
            # Only show the most critical missing skills (from required_skills field)
            required_skills_text = job.get('details', {}).get('required_skills', '').lower()
            critical_missing = [s for s in analysis['missing_skills'] if s in required_skills_text]
            if critical_missing:
                print(f"    ❌ Critical Missing: {', '.join(critical_missing)}")

    # 6. Save the final, enriched, and sorted data to the output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(enriched_jobs, f, ensure_ascii=False, indent=4)
        print(f"\n\n✅ Success! Enriched data for {len(enriched_jobs)} jobs saved to '{OUTPUT_FILE}'")
    except Exception as e:
        print(f"\n❌ ERROR: Could not save the output file. Reason: {e}")


if __name__ == "__main__":
    main()