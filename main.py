import os
import json
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs
from backend.scraper import scrape_jobs


if __name__ == "__main__":
    # Editable parameters for quick experimentation
    TOP_K = 10
    BASE_DIR = os.path.dirname(__file__)
    INDEX_PREFIX = os.path.join(BASE_DIR, "backend", "jobs_index")
    RESUME_PATH = os.path.join(BASE_DIR, "templates", "resume.tex")

    # 1) Always scrape (interactive)
    print("Starting scraping session... (interactive)")
    JOBS_PATH = scrape_jobs()
    print(f"Scraped jobs saved to: {JOBS_PATH}")

    # 2) Build/refresh FAISS index
    meta = vectorize_jobs(jobs_json_path=JOBS_PATH, output_prefix=INDEX_PREFIX)
    print("Index built:", json.dumps({k: meta[k] for k in ["num_vectors", "model_name", "dim"]}, indent=2))

    # 3) Match resume against index
    results = match_resume_to_jobs(resume_path=RESUME_PATH, index_prefix=INDEX_PREFIX, top_k=TOP_K)
    print(json.dumps({"top_k": TOP_K, "results": results}, ensure_ascii=False, indent=2))