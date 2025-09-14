## WaterlooActuallyWorks
Automates scraping WaterlooWorks, matching jobs to your resume, and generating personalized LaTeX resume/cover letters true to your resume.

### Quick start
1) Create `.env` with your Anthropic key:
```bash
echo "ANTHROPIC_API_KEY=sk-..." > .env
```
2) Install deps (uv):
```bash
uv sync && source .venv/bin/activate
```
3) Install Playwright browsers (one‑time):
```bash
uv run playwright install
```
4) Put your templates at `templates/resume.tex` and `templates/cover_letter.tex`. Adjust `config/config.yaml` (`max_jobs`, `top_k`, paths).
5) Run GUI (recommended):
```bash
uv run ui.py
```
6) Or run the CLI pipeline:
```bash
uv run main.py
```

### What to expect
- A Chromium window opens; log in to WaterlooWorks and navigate to co‑op jobs. Scraping proceeds automatically up to `max_jobs`.
- Personalized `.tex` (and PDFs when Tectonic is available) are written to `outputs/personalized/`.

### Notes
- PDFs: the CLI auto‑prepares Tectonic when possible; otherwise `.tex` is saved and a log is written.
- Optional constraints: use `templates/constraints.txt` or paste into the GUI to influence matching.