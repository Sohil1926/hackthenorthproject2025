import os, json, re, subprocess
from typing import List, Dict, Any

from anthropic import Anthropic


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _extract_latex(text: str) -> str:
    """Extract LaTeX code from LLM response, handling markdown code blocks and explanatory text."""
    if not text:
        return ""
    
    # Try to find LaTeX in markdown code blocks first
    latex_block = re.search(r'```(?:latex|tex)?\s*\n(.*?)\n```', text, re.DOTALL)
    if latex_block:
        return latex_block.group(1).strip()
    
    # Try to find content between \documentclass and \end{document}
    latex_content = re.search(r'\\documentclass.*?\\end\{document\}', text, re.DOTALL)
    if latex_content:
        return latex_content.group(0).strip()
    
    # If nothing found, return the whole text (maybe it's already pure LaTeX)
    return text.strip()


def _compile_tex(tex_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    try:
        subprocess.run(["/Library/TeX/texbin/pdflatex", "-interaction=nonstopmode", "-output-directory", out_dir, tex_path], cwd=out_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return os.path.splitext(os.path.join(out_dir, os.path.basename(tex_path)))[0] + ".pdf"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"      Warning: PDF compilation failed ({e}). LaTeX file saved at {tex_path}")
        return tex_path


def personalize_resume_and_cover_letter(
    resume_tex_path: str,
    cover_letter_tex_path: str,
    jobs_json_path: str,
    selected_job_ids: List[str],
    out_dir: str,
    model: str = "claude-4-sonnet",
) -> List[str]:
    resume_base, cover_base = _read(resume_tex_path), _read(cover_letter_tex_path)
    with open(jobs_json_path, "r", encoding="utf-8") as f:
        jobs: List[Dict[str, Any]] = json.load(f)
    by_id = {str(j["id"]): j for j in jobs}
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    pdfs: List[str] = []
    print(f"Personalizing resume and cover letter for {len(selected_job_ids)} jobs...")
    for i, jid in enumerate(selected_job_ids, 1):
        job = by_id.get(str(jid))
        if not job:
            print(f"  Job {i}/{len(selected_job_ids)} (ID: {jid}): Not found in jobs data, skipping")
            continue
        print(f"  Job {i}/{len(selected_job_ids)} (ID: {jid}): Generating with LLM...")
        
        # Generate resume
        resume_prompt = f"Generate a complete LaTeX resume for this job. Use the base template style but personalize for this specific role:\n\nJob: {json.dumps(job, indent=2)}\n\nBase template:\n{resume_base}\n\nReturn ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}:"
        resume_msg = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": resume_prompt}])
        resume_response = resume_msg.content[0].text if resume_msg.content else ""
        resume_tex = _extract_latex(resume_response) or resume_base
        
        # Generate cover letter  
        cover_prompt = f"Generate a complete LaTeX cover letter for this job. Use the base template style but personalize for this specific role:\n\nJob: {json.dumps(job, indent=2)}\n\nBase template:\n{cover_base}\n\nReturn ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}:"
        cover_msg = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": cover_prompt}])
        cover_response = cover_msg.content[0].text if cover_msg.content else ""
        cover_tex = _extract_latex(cover_response) or cover_base
        job_slug = str(jid)
        out_base = os.path.abspath(os.path.join(out_dir, job_slug))
        os.makedirs(out_dir, exist_ok=True)
        r_path, c_path = out_base + "_resume.tex", out_base + "_cover_letter.tex"
        with open(r_path, "w", encoding="utf-8") as rf:
            rf.write(resume_tex)
        with open(c_path, "w", encoding="utf-8") as cf:
            cf.write(cover_tex)
        print(f"    Compiling resume PDF...")
        resume_pdf = _compile_tex(r_path, out_dir)
        print(f"    Compiling cover letter PDF...")
        cover_pdf = _compile_tex(c_path, out_dir)
        pdfs += [resume_pdf, cover_pdf]
    print(f"Personalization complete! Generated {len(pdfs)} PDFs in {out_dir}")
    return pdfs


__all__ = ["personalize_resume_and_cover_letter"]

