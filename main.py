# modularized functions from backend folder
from backend.scraper import scrape_jobs
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs

if __name__ == "__main__":
    # scrape jobs
    # potential: do deterministic filtering of jobs based on location, job title, compensation, etc.
    # vectorize jobs and match template resume to jobs, return id's of top n matches
    # potential: do further filtering based on LLM choice and human constraint description.
    # use LLM to personalize the /template/resume.tex and /template/cover_letter.tex to selected id's
    # return the personalized resume and cover letter to selected id's