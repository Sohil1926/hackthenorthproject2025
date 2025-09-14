import os, json, re, subprocess, asyncio
from typing import List, Dict, Any

from anthropic import AsyncAnthropic


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
    model: str,
) -> List[str]:
    resume_base, cover_base = _read(resume_tex_path), _read(cover_letter_tex_path)
    with open(jobs_json_path, "r", encoding="utf-8") as f:
        jobs: List[Dict[str, Any]] = json.load(f)
    by_id = {str(j["id"]): j for j in jobs}

    async def generate_docs(job, jid):
        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        resume_prompt = f"Generate a complete LaTeX resume for this job. Use the base template style but personalize for this specific role:\n\nJob: {json.dumps(job, indent=2)}\n\nBase template (copy this structure verbatim, including preamble, packages, fonts, margins, macros, and formatting; only change textual content):\n{resume_base}\n\nReturn ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}. Do not include markdown or explanations."
        cover_prompt = f"Generate a complete LaTeX cover letter for this job. Use the base template style but personalize for this specific role:\n\nJob: {json.dumps(job, indent=2)}\n\nBase template (copy this structure verbatim, including preamble, packages, fonts, margins, macros, and formatting; only change textual content):\n{cover_base}\n\nReturn ONLY the complete LaTeX code starting with \\documentclass and ending with \\end{{document}}. Do not include markdown or explanations."
        
        resume_task = client.messages.create(model=model, max_tokens=4000, temperature=0, messages=[{"role": "user", "content": resume_prompt}])
        cover_task = client.messages.create(model=model, max_tokens=4000, temperature=0, messages=[{"role": "user", "content": cover_prompt}])
        resume_msg, cover_msg = await asyncio.gather(resume_task, cover_task)
        
        resume_tex = _extract_latex(resume_msg.content[0].text if resume_msg.content else "") or resume_base
        cover_tex = _extract_latex(cover_msg.content[0].text if cover_msg.content else "") or cover_base
        
        job_slug = str(jid)
        out_base = os.path.abspath(os.path.join(out_dir, job_slug))
        os.makedirs(out_dir, exist_ok=True)
        r_path, c_path = out_base + "_resume.tex", out_base + "_cover_letter.tex"
        
        with open(r_path, "w", encoding="utf-8") as rf:
            rf.write(resume_tex)
        with open(c_path, "w", encoding="utf-8") as cf:
            cf.write(cover_tex)
            
        resume_pdf = _compile_tex(r_path, out_dir)
        cover_pdf = _compile_tex(c_path, out_dir)
        print(f"  Job {jid}: Generated resume + cover letter")
        return [resume_pdf, cover_pdf]

    async def process_all():
        tasks = []
        for jid in selected_job_ids:
            job = by_id.get(str(jid))
            if job:
                tasks.append(generate_docs(job, jid))
        return await asyncio.gather(*tasks)
    
    print(f"Generating documents for {len(selected_job_ids)} jobs in parallel...")
    all_results = asyncio.run(process_all())
    pdfs = [pdf for result in all_results for pdf in result]
    print(f"Complete! Generated {len(pdfs)} PDFs in {out_dir}")
    return pdfs


__all__ = ["personalize_resume_and_cover_letter"]

