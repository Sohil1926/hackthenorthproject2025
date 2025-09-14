import os
import json
import yaml
from dotenv import load_dotenv
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs
from backend.scraper import scrape_jobs
from backend.personalizer import personalize_resume_and_cover_letter

# TO ADD:
# deterministic filtering of jobs based on location, job title, compensation, etc.
# add textbox to the vectorizer
# apply to the jobs


if __name__ == "__main__":
    # Editable parameters for quick experimentation
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    load_dotenv()
    with open(CONFIG_PATH, "r", encoding="utf-8") as cf:
        cfg = yaml.safe_load(cf)

    TOP_K = cfg["top_k"]
    MAX_JOBS = cfg["max_jobs"]
    BASE_DIR = os.path.dirname(__file__)
    INDEX_PREFIX = os.path.abspath(os.path.join(BASE_DIR, cfg["index_prefix"]))
    RESUME_PATH = os.path.abspath(os.path.join(BASE_DIR, cfg["resume_path"]))
    COVER_PATH = os.path.abspath(os.path.join(BASE_DIR, cfg["cover_path"]))
    PERSONALIZE_MODEL = cfg["personalize_model"]
    EMBED_MODEL = cfg["embed_model"]
    PERSONALIZED_DIR = os.path.abspath(os.path.join(BASE_DIR, cfg["personalized_dir"]))

    # 1) Always scrape (interactive)
    print("Starting scraping session... (interactive)")
    JOBS_PATH = scrape_jobs(max_jobs=MAX_JOBS)
    print(f"Scraped jobs saved to: {JOBS_PATH}")

    # 2) Build/refresh FAISS index
    meta = vectorize_jobs(jobs_json_path=JOBS_PATH, output_prefix=INDEX_PREFIX, model_name=EMBED_MODEL)
    print("Index built:", json.dumps({k: meta[k] for k in ["num_vectors", "model_name", "dim"]}, indent=2))

    # 3) Match resume against index
    results = match_resume_to_jobs(resume_path=RESUME_PATH, index_prefix=INDEX_PREFIX, top_k=TOP_K)
    print(json.dumps({"top_k": TOP_K, "results": results}, ensure_ascii=False, indent=2))

    # 4) Personalize the resume and cover letter to the selected id's
    selected_ids = [r["job_id"] for r in results]
    personalize_resume_and_cover_letter(
        RESUME_PATH,
        COVER_PATH,
        JOBS_PATH,
        selected_ids,
        out_dir=PERSONALIZED_DIR,
        model=PERSONALIZE_MODEL,
    )