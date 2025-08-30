# integrate.py (Version 3.0 - The Perfect Integrator)

import json
import os
from tqdm import tqdm  # For the progress bar

# Import the ultimate JobMatcher class from our new matcher.py
from matcher import JobMatcher

# --- Configuration ---
JOBS_INPUT_FILE = "waterlooworks_jobs.json"
RESUME_FILE = "resume.pdf"  # <-- IMPORTANT: Make sure this file exists!
OUTPUT_FILE = "jobs_with_scores.json"

def main():
    """
    Loads scraped jobs, enriches them with AI-powered match analysis using the
    JobMatcher, and saves the sorted, production-ready results.
    """
    print("--- Starting Phase 2: AI Integration & Scoring ---")

    # 1. Load the raw job data from your scraper's output
    try:
        with open(JOBS_INPUT_FILE, 'r', encoding='utf-8') as f:
            all_jobs = json.load(f)
        print(f"✅ Successfully loaded {len(all_jobs)} jobs from '{JOBS_INPUT_FILE}'")
    except FileNotFoundError:
        print(f"❌ ERROR: The input file '{JOBS_INPUT_FILE}' was not found.")
        print("-> Please run your scraper.py script first to generate it.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERROR: Could not parse JSON in '{JOBS_INPUT_FILE}'. It might be empty or corrupted.")
        return

    # 2. Initialize the JobMatcher with your resume.
    # This is the most efficient way, as the resume is processed only once.
    try:
        matcher = JobMatcher(resume_path=RESUME_FILE)
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        print(f"-> Please add your resume as '{RESUME_FILE}' to the project folder.")
        return

    # 3. Process each job and enrich it with the match analysis
    enriched_jobs = []
    
    # tqdm provides a clean, real-time progress bar in the terminal
    for job in tqdm(all_jobs, desc="🤖 Analyzing jobs"):
        # The matcher returns a rich dictionary with score, skills, notes, etc.
        match_analysis = matcher.calculate_match(job)
        
        # Create a new dictionary to hold the final, enriched job data
        enriched_job = job.copy()
        enriched_job['match_analysis'] = match_analysis
        enriched_jobs.append(enriched_job)

    # 4. Sort the final list of jobs by score, from highest to lowest
    enriched_jobs.sort(key=lambda x: x['match_analysis']['score'], reverse=True)

    # 5. Print a detailed, actionable summary of the top 5 matches
    print("\n--- Top 5 Job Matches ---")
    for job in enriched_jobs[:5]:
        analysis = job['match_analysis']
        print(f"\n  - {analysis['score']}%: {job['title']} @ {job['company']}")
        
        if analysis['matched_skills']:
            print(f"    ✅ Matched Skills: {', '.join(analysis['matched_skills'])}")
        
        if analysis['missing_skills']:
            # Highlight missing skills to show areas for improvement or filtering
            print(f"    ❌ Missing Skills: {', '.join(analysis['missing_skills'])}")
        
        if "Penalty applied" in analysis['notes']:
            print(f"    ⚠️ Note: {analysis['notes']}")

    # 6. Save the final, enriched, and sorted data to the output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(enriched_jobs, f, ensure_ascii=False, indent=4)
        print(f"\n\n✅ Success! Enriched data for {len(enriched_jobs)} jobs saved to '{OUTPUT_FILE}'")
        print("-> This file is now ready for the backend database in Phase 3.")
    except Exception as e:
        print(f"\n❌ ERROR: Could not save the output file. Reason: {e}")


if __name__ == "__main__":
    main()