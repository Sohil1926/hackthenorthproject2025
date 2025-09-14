import os
import json
import yaml
import shutil
import subprocess
import sys
import tempfile
import stat
import platform
import urllib.request
import tarfile
import zipfile
from dotenv import load_dotenv

# Suppress tokenizer parallelism warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs
from backend.scraper import scrape_jobs
from backend.personalizer import personalize_resume_and_cover_letter

# TO ADD:
# deterministic filtering of jobs based on location, job title, compensation, etc.
# add textbox to the vectorizer
# apply to the jobs


if __name__ == "__main__":
    def _ensure_tectonic() -> str:
        """Download/cache a portable Tectonic binary if not available on PATH.
        Returns absolute path to the executable or empty string on failure.
        """
        # 1) PATH
        path = shutil.which("tectonic")
        if path:
            return path

        # 2) Cached binary
        base_dir = os.path.dirname(__file__)
        cache_dir = os.path.join(base_dir, ".cache", "tectonic")
        os.makedirs(cache_dir, exist_ok=True)
        exe_name = "tectonic.exe" if platform.system() == "Windows" else "tectonic"
        cached_path = os.path.join(cache_dir, exe_name)
        if os.path.exists(cached_path):
            return cached_path

        # 3) Download from GitHub releases (portable builds)
        system = platform.system()
        machine = platform.machine().lower()
        if system == "Darwin":
            asset = "tectonic-0.15.0-x86_64-apple-darwin.tar.gz" if "x86_64" in machine else "tectonic-0.15.0-aarch64-apple-darwin.tar.gz"
        elif system == "Linux":
            asset = "tectonic-0.15.0-x86_64-unknown-linux-gnu.tar.gz"
        elif system == "Windows":
            asset = "tectonic-0.15.0-x86_64-pc-windows-msvc.zip"
        else:
            return ""

        url = f"https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/{asset}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive_path = os.path.join(tmp, asset)
                urllib.request.urlretrieve(url, archive_path)
                if archive_path.endswith('.zip'):
                    with zipfile.ZipFile(archive_path) as zf:
                        zf.extractall(tmp)
                else:
                    with tarfile.open(archive_path) as tf:
                        tf.extractall(tmp)

                for root, _dirs, files in os.walk(tmp):
                    if exe_name in files:
                        src = os.path.join(root, exe_name)
                        shutil.copy2(src, cached_path)
                        os.chmod(cached_path, os.stat(cached_path).st_mode | stat.S_IXUSR)
                        return cached_path
        except Exception:
            return ""

        return ""

    def setup_dependencies() -> None:
        # Pre-fetch Tectonic and export path for downstream use
        path = _ensure_tectonic()
        if path:
            os.environ["TECTONIC_BIN"] = path
            print(f"Tectonic available at: {path}")
        else:
            print("Warning: Could not prepare Tectonic; LaTeX will not be compiled to PDF.")

    def test_setup() -> None:
        # Try `tectonic --version` using the prepared binary or PATH
        bin_path = os.environ.get("TECTONIC_BIN") or shutil.which("tectonic")
        if not bin_path:
            print("Setup test: Tectonic not found. PDFs will not be built.")
            return
        try:
            res = subprocess.run([bin_path, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            line = res.stdout.splitlines()[0] if res.stdout else ""
            print(f"Setup test: {line}")
        except Exception as e:
            print(f"Setup test: Failed to run Tectonic ({e})")

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

    # 0) Setup external dependencies (non-interactive)
    setup_dependencies()
    test_setup()

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