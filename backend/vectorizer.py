import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

import numpy as np

# Use faiss-cpu package
import faiss  # type: ignore
from sentence_transformers import SentenceTransformer


def read_jobs_json(jobs_json_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(jobs_json_path):
        raise FileNotFoundError(f"Jobs JSON not found at: {jobs_json_path}")
    with open(jobs_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected jobs JSON to be a list of job objects")
    return data


def job_to_text(job: Dict[str, Any]) -> str:
    # Flatten key textual fields into a single corpus string
    parts: List[str] = []
    title = job.get("title") or job.get("details", {}).get("job_title")
    if title:
        parts.append(str(title))
    company = job.get("company") or job.get("details", {}).get("organization")
    if company:
        parts.append(str(company))

    details = job.get("details", {})
    # Common rich fields
    for key in (
        "job_summary",
        "job_responsibilities",
        "required_skills",
        "additional_information",
        "compensation_and_benefits",
        "targeted_degrees_and_disciplines",
    ):
        if key in details and details[key]:
            parts.append(str(details[key]))

    # Fallback: include any remaining short string fields in details
    for k, v in details.items():
        if k in {
            "job_title",
            "job_summary",
            "job_responsibilities",
            "required_skills",
            "additional_information",
            "compensation_and_benefits",
            "targeted_degrees_and_disciplines",
        }:
            continue
        if isinstance(v, str) and len(v) > 0 and len(v) <= 2000:
            parts.append(v)

    return " \n ".join(parts)


def build_embeddings(
    texts: List[str],
    model_name: str,
    batch_size: int = 64,
) -> np.ndarray:
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
      texts,
      batch_size=batch_size,
      show_progress_bar=True,
      convert_to_numpy=True,
    )
    # Normalize to use cosine similarity via inner product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms
    return embeddings.astype("float32")


def build_faiss_index(embeddings: np.ndarray, ids: List[int]) -> faiss.Index:
    dim = embeddings.shape[1]
    base_index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap2(base_index)
    ids_array = np.asarray(ids, dtype="int64")
    index.add_with_ids(embeddings, ids_array)
    return index


def save_index(index: faiss.Index, meta: Dict[str, Any], output_prefix: str) -> None:
    index_path = f"{output_prefix}.faiss"
    meta_path = f"{output_prefix}.meta.json"
    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main() -> None:
    base_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(description="Build FAISS index for WaterlooWorks jobs")
    parser.add_argument(
        "--input",
        default=os.path.join(base_dir, "waterlooworks_jobs.json"),
        help="Path to jobs JSON (default: backend/waterlooworks_jobs.json)",
    )
    parser.add_argument(
        "--output-prefix",
        default=os.path.join(base_dir, "jobs_index"),
        help="Output prefix for index and metadata (default: backend/jobs_index)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WAT_MATCH_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        help="SentenceTransformer model name",
    )
    parser.add_argument(
        "--batch-size", type=int, default=64, help="Embedding batch size"
    )
    args = parser.parse_args()

    print("Loading jobs...")
    jobs = read_jobs_json(args.input)
    print(f"Loaded {len(jobs)} jobs")

    print("Preparing texts...")
    texts: List[str] = [job_to_text(job) for job in jobs]
    # Map internal numeric ids to external job ids (which are strings)
    internal_ids: List[int] = list(range(len(jobs)))
    id_to_job_id = {str(i): str(jobs[i].get("id", i)) for i in internal_ids}

    print(f"Encoding {len(texts)} texts with model: {args.model}")
    embeddings = build_embeddings(texts, args.model, batch_size=args.batch_size)

    print("Building FAISS index (cosine via inner product)...")
    index = build_faiss_index(embeddings, internal_ids)

    meta = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "model_name": args.model,
        "num_vectors": len(texts),
        "dim": int(embeddings.shape[1]),
        "id_to_job_id": id_to_job_id,
        "source": os.path.abspath(args.input),
    }

    print(f"Saving index and metadata to prefix: {args.output_prefix}")
    save_index(index, meta, args.output_prefix)
    print("Done.")


if __name__ == "__main__":
    main()


