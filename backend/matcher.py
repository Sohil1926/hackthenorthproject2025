import os
import argparse
import json
from typing import List, Dict, Any, Tuple

import numpy as np
import faiss  # type: ignore


def read_file_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    # Basic extractor for .tex or .txt; if PDF is needed, we can extend
    _, ext = os.path.splitext(path)
    if ext.lower() in {".tex", ".txt", ".md"}:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext.lower() == ".pdf":
        try:
            import fitz  # PyMuPDF
        except Exception as e:
            raise RuntimeError("PyMuPDF is required to read PDFs. Install PyMuPDF or provide a .tex/.txt resume.") from e
        doc = fitz.open(path)
        return "".join(page.get_text() for page in doc)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def build_query_embedding(text: str, model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    emb = model.encode([text], convert_to_numpy=True)
    # Normalize for cosine via inner product
    norm = np.linalg.norm(emb, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    emb = emb / norm
    return emb.astype("float32")


def load_index(prefix: str) -> Tuple[faiss.Index, Dict[str, Any]]:
    index_path = f"{prefix}.faiss"
    meta_path = f"{prefix}.meta.json"
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise FileNotFoundError(f"Index or metadata not found for prefix: {prefix}")
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta


def search(index: faiss.Index, query_vec: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
    distances, ids = index.search(query_vec, top_k)
    return distances[0], ids[0]


def match_resume_to_jobs(
    resume_path: str,
    index_prefix: str,
    top_k: int = 10,
    model_name: str = os.environ.get("WAT_MATCH_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
) -> List[Dict[str, Any]]:
    """
    Load FAISS index and metadata, embed resume, and return top-k job matches as
    a list of {job_id, score} sorted by score desc.
    """
    index, meta = load_index(index_prefix)
    text = read_file_text(resume_path)
    q = build_query_embedding(text, model_name)
    distances, ids = search(index, q, top_k)
    id_to_job_id: Dict[str, str] = meta.get("id_to_job_id", {})
    results: List[Dict[str, Any]] = []
    for score, internal_id in zip(distances.tolist(), ids.tolist()):
        if internal_id == -1:
            continue
        job_id = id_to_job_id.get(str(internal_id), str(internal_id))
        results.append({"job_id": job_id, "score": float(score)})
    return results


def main() -> None:
    base_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(description="Query FAISS index with resume to get top-K job IDs")
    parser.add_argument(
        "--index-prefix",
        default=os.path.join(base_dir, "jobs_index"),
        help="Path prefix to FAISS index and metadata (default: backend/jobs_index)",
    )
    parser.add_argument(
        "--resume",
        default=os.path.join(os.path.dirname(base_dir), "templates", "resume.tex"),
        help="Path to resume (.tex/.txt/.md or .pdf)",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Number of top matches to return")
    parser.add_argument(
        "--model",
        default=os.environ.get("WAT_MATCH_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        help="SentenceTransformer model name to ensure compatibility with the index",
    )
    parser.add_argument("--print", action="store_true", help="Print top results with scores")
    args = parser.parse_args()

    results = match_resume_to_jobs(
        resume_path=args.resume,
        index_prefix=args.index_prefix,
        top_k=args.top_k,
        model_name=args.model,
    )

    print(json.dumps({"top_k": args.top_k, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


