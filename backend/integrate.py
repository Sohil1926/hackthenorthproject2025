# integrate.py

import json
# Import the functions from your matcher.py file
from matcher import extract_text_from_pdf, extract_skills, calculate_match_score

# --- Configuration ---
JOBS_INPUT_FILE = "waterlooworks_jobs.json"
RESUME_FILE = "my_resume.pdf"  # <--- IMPORTANT: Make sure this file exists!
OUTPUT_FILE = "jobs_with_scores.json"

def combine_job_details_to_text(job_data):
    """Combines relevant fields from a job's details into a single string."""
    details = job_data.get('details', {})
    if "error" in details:
        return ""

    # We prioritize the most skill-heavy fields
    text_parts = [
        details.get('job_title', ''),
        details.get('job_summary', ''),
        details.get('job_responsibilities', ''),
        details.get('required_skills', ''),
        details.get('targeted_degrees_and_disciplines', '')
    ]
    
    # Join all parts into a single lowercase string
    return " ".join(str(part) for part in text_parts).lower()

def main():
    """
    Main function to load jobs, match them against a resume, and save the results.
    """
    print("--- Starting Phase 2 Integration ---")

    # 1. Load the scraped jobs data
    try:
        with open(JOBS_INPUT_FILE, 'r', encoding='utf-8') as f:
            all_jobs = json.load(f)
        print(f"✅ Successfully loaded {len(all_jobs)} jobs from {JOBS_INPUT_FILE}")
    except FileNotFoundError:
        print(f"❌ ERROR: The input file '{JOBS_INPUT_FILE}' was not found.")
        print("Please run the scraper.py script first to generate it.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERROR: Could not parse the JSON in '{JOBS_INPUT_FILE}'. It might be empty or corrupted.")
        return

    # 2. Process the resume
    try:
        resume_text = extract_text_from_pdf(RESUME_FILE)
        resume_skills = extract_skills(resume_text)
        print(f"✅ Successfully processed resume. Found {len(resume_skills)} unique skills.")
        print(f"   Skills: {resume_skills}")
    except FileNotFoundError:
        print(f"❌ ERROR: The resume file '{RESUME_FILE}' was not found.")
        print("Please add your resume to the project folder and update the filename if needed.")
        return

    # 3. Iterate, score, and enrich each job
    print("\nScoring jobs against your resume...")
    for job in all_jobs:
        if "error" in job.get('details', {}):
            job['match_score'] = 0.0
            continue

        job_text = combine_job_details_to_text(job)
        job_skills = extract_skills(job_text)
        
        score = calculate_match_score(resume_skills, job_skills)
        job['match_score'] = round(score, 2)
        
        print(f"  - Scored Job ID {job['id']} ({job['title']}): {job['match_score']}%")

    # 4. Sort jobs by match score (highest first)
    all_jobs.sort(key=lambda x: x['match_score'], reverse=True)
    print("\nTop 5 matching jobs:")
    for job in all_jobs[:5]:
        print(f"  - {job['match_score']}%: {job['title']} at {job['company']}")

    # 5. Save the enriched data to a new file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=4)
    
    print(f"\n✅ Integration complete! Enriched job data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()