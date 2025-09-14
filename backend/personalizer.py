import os, json, re, subprocess
from typing import List, Dict, Any

from anthropic import Anthropic


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _compile_tex(tex_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-output-directory", out_dir, tex_path], cwd=out_dir, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return os.path.splitext(os.path.join(out_dir, os.path.basename(tex_path)))[0] + ".pdf"


def personalize_resume_and_cover_letter(
    resume_tex_path: str,
    cover_letter_tex_path: str,
    jobs_json_path: str,
    selected_job_ids: List[str],
    out_dir: str,
    model: str,
) -> List[str]:
    resume_base, cover_base = _read(resume_tex_path), _read(cover_letter_tex_path)
    with open(jobs_json_path, "r", encoding="utf-8") as f:
        jobs: List[Dict[str, Any]] = json.load(f)
    by_id = {str(j["id"]): j for j in jobs}
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    pdfs: List[str] = []
    for jid in selected_job_ids:
        job = by_id.get(str(jid))
        if not job:
            continue
        prompt = (
            "Personalize the LaTeX resume and cover letter for this job. "
            "Return ONLY two LaTeX docs wrapped as <RESUME>...</RESUME> and <COVER>...</COVER>. "
            "Keep compilable LaTeX and relevant, specific tailoring.\n\n"
            f"JOB_JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nBASELINE_RESUME:\n{resume_base}\n\nBASELINE_COVER:\n{cover_base}"
        )
        msg = client.messages.create(model=model, max_tokens=12000, temperature=0.2, messages=[{"role": "user", "content": prompt}])
        text = "".join([c.text for c in msg.content if hasattr(c, "text")]) if hasattr(msg, "content") else ""
        res_m = re.search(r"<RESUME>([\s\S]*?)</RESUME>", text) or re.search(r"```(?:latex|tex)?([\s\S]*?)```", text)
        cov_m = re.search(r"<COVER>([\s\S]*?)</COVER>", text)
        resume_tex = (res_m.group(1) if res_m else text).strip()
        cover_tex = (cov_m.group(1) if cov_m else cover_base).strip()
        job_slug = str(jid)
        out_base = os.path.abspath(os.path.join(out_dir, job_slug))
        os.makedirs(out_dir, exist_ok=True)
        r_path, c_path = out_base + "_resume.tex", out_base + "_cover_letter.tex"
        with open(r_path, "w", encoding="utf-8") as rf:
            rf.write(resume_tex)
        with open(c_path, "w", encoding="utf-8") as cf:
            cf.write(cover_tex)
        pdfs += [_compile_tex(r_path, out_dir), _compile_tex(c_path, out_dir)]
    return pdfs


__all__ = ["personalize_resume_and_cover_letter"]

