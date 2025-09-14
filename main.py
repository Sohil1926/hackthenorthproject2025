import os
import json
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs


def run(end_to_end_top_k: int = 10) -> None:
    base_dir = os.path.dirname(__file__)
    jobs_path = os.path.join(base_dir, "backend", "waterlooworks_jobs.json")
    index_prefix = os.path.join(base_dir, "backend", "jobs_index")
    resume_path = os.path.join(base_dir, "templates", "resume.tex")

    # Build or refresh the index
    meta = vectorize_jobs(jobs_json_path=jobs_path, output_prefix=index_prefix)
    print("Index built:", json.dumps({k: meta[k] for k in ["num_vectors", "model_name", "dim"]}, indent=2))

    # Match
    results = match_resume_to_jobs(resume_path=resume_path, index_prefix=index_prefix, top_k=end_to_end_top_k)
    print(json.dumps({"top_k": end_to_end_top_k, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run(10)