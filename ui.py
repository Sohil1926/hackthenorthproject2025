import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import yaml
from dotenv import load_dotenv

# Reuse existing backend functions
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs
from backend.scraper import scrape_jobs
from backend.personalizer import personalize_resume_and_cover_letter

# Suppress tokenizer parallelism warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class WatMatchUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WAT-Match Automator")
        self.geometry("900x640")
        self.resizable(True, True)

        # Light theme styling
        self.configure(bg="#ffffff")
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background='#ffffff')
        style.configure('TLabel', background='#ffffff', foreground='#111111')
        style.configure('TButton', padding=8)
        style.configure('Accent.TButton', padding=10, background='#2563eb', foreground='#ffffff')
        style.map('Accent.TButton', background=[('active', '#1d4ed8')])
        style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', foreground='#111111')
        style.configure('Treeview.Heading', font=('Helvetica', 10, 'bold'))

        # Load config
        base_dir = os.path.dirname(__file__)
        self.config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(self.config_path, "r", encoding="utf-8") as cf:
            self.cfg = yaml.safe_load(cf)

        # Load environment variables (e.g., ANTHROPIC_API_KEY)
        load_dotenv()

        # State
        self.run_thread = None
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.result_summary = []

        # UI Elements
        self._build_form()
        # Actions above log so Start is always visible
        self._build_actions()
        self._build_log()
        self._build_summary_panel()

        # Poll logs
        self.after(100, self._drain_log_queue)

    def _build_form(self):
        form = ttk.Frame(self, padding=12)
        form.pack(fill=tk.X)

        # Max Jobs
        ttk.Label(form, text="Max jobs to scrape:").grid(row=0, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.max_jobs_var = tk.IntVar(value=int(self.cfg.get("max_jobs", 10)))
        self.max_jobs_spin = ttk.Spinbox(form, from_=1, to=10000, textvariable=self.max_jobs_var, width=10)
        self.max_jobs_spin.grid(row=0, column=1, sticky=tk.W, pady=4)

        # Top K
        ttk.Label(form, text="Top K matches:").grid(row=1, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.topk_var = tk.IntVar(value=int(self.cfg.get("top_k", 3)))
        self.topk_spin = ttk.Spinbox(form, from_=1, to=1000, textvariable=self.topk_var, width=10)
        self.topk_spin.grid(row=1, column=1, sticky=tk.W, pady=4)

        # Constraints
        ttk.Label(form, text="Constraints (influences matching):").grid(row=2, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.constraints_text = scrolledtext.ScrolledText(form, width=60, height=8, wrap=tk.WORD, background="#ffffff", foreground="#111111", insertbackground="#111111")
        self.constraints_text.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E)

        # Prefill constraints from file if set
        constraints_path = self.cfg.get("constraints_path")
        if constraints_path:
            try:
                abs_constraints = os.path.abspath(os.path.join(os.path.dirname(__file__), constraints_path))
                if os.path.exists(abs_constraints):
                    with open(abs_constraints, "r", encoding="utf-8", errors="ignore") as f:
                        self.constraints_text.insert("1.0", f.read())
            except Exception:
                pass

        for i in range(3):
            form.grid_columnconfigure(i, weight=0)

    def _build_log(self):
        frame = ttk.LabelFrame(self, text="Log", padding=8, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,8))
        self.log_area = scrolledtext.ScrolledText(frame, state=tk.DISABLED, width=80, height=16, wrap=tk.WORD, background="#ffffff", foreground="#111111", insertbackground="#111111")
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _build_actions(self):
        bar = ttk.Frame(self, padding=12, style='TFrame')
        bar.pack(fill=tk.X)
        self.start_btn = ttk.Button(bar, text="Start", command=self._on_start, style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT)

    def _build_summary_panel(self):
        frame = ttk.LabelFrame(self, text="Applications", padding=8, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=(0,12))
        self.summary_frame = frame
        columns = ("company", "title")
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=6)
        tree.heading('company', text='Company')
        tree.heading('title', text='Title')
        tree.column('company', width=220, anchor='w')
        tree.column('title', width=520, anchor='w')
        tree.pack(fill=tk.BOTH, expand=True)
        self.summary_tree = tree
        self.summary_count_label = ttk.Label(frame, text="Applications: 0")
        self.summary_count_label.pack(anchor='w', pady=(6,0))

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _drain_log_queue(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_area.configure(state=tk.NORMAL)
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state=tk.DISABLED)
        self.after(100, self._drain_log_queue)

    def _on_start(self):
        if self.run_thread and self.run_thread.is_alive():
            messagebox.showinfo("Busy", "A run is already in progress.")
            return
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.result_summary = []
        # Clear applications panel
        try:
            for iid in self.summary_tree.get_children():
                self.summary_tree.delete(iid)
            self.summary_count_label.configure(text="Applications: 0")
        except Exception:
            pass

        max_jobs = int(self.max_jobs_var.get())
        top_k = int(self.topk_var.get())
        constraints_text = self.constraints_text.get("1.0", tk.END).strip()

        # If missing, inform the user to populate .env, but do not prompt
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            messagebox.showerror("Missing API Key", "Set ANTHROPIC_API_KEY in your .env, then restart.")
            return

        self.run_thread = threading.Thread(target=self._run_pipeline, args=(max_jobs, top_k, constraints_text), daemon=True)
        self.run_thread.start()

    def _run_pipeline(self, max_jobs: int, top_k: int, constraints_text: str):
        try:
            base_dir = os.path.dirname(__file__)
            cfg = self.cfg

            # Write constraints to a temp file alongside configured path, if provided
            constraints_path_cfg = cfg.get("constraints_path")
            constraints_path = None
            if constraints_text:
                if constraints_path_cfg:
                    constraints_path = os.path.abspath(os.path.join(base_dir, constraints_path_cfg))
                else:
                    constraints_path = os.path.join(base_dir, "templates", "constraints.txt")
                os.makedirs(os.path.dirname(constraints_path), exist_ok=True)
                with open(constraints_path, "w", encoding="utf-8") as f:
                    f.write(constraints_text)

            # 1) Scrape
            self._log("Starting scraping session... (browser will open; login then navigate to jobs)")
            jobs_path = scrape_jobs(max_jobs=max_jobs)
            self._log(f"Scraped jobs saved to: {jobs_path}")

            # 2) Vectorize
            self._log("Building/refreshing FAISS index...")
            index_prefix = os.path.abspath(os.path.join(base_dir, cfg["index_prefix"]))
            meta = vectorize_jobs(jobs_json_path=jobs_path, output_prefix=index_prefix, model_name=cfg["embed_model"])
            self._log(f"Index built: {json.dumps({k: meta[k] for k in ['num_vectors','model_name','dim']})}")

            # 3) Match
            self._log("Matching resume to jobs...")
            resume_path = os.path.abspath(os.path.join(base_dir, cfg["resume_path"]))
            results = match_resume_to_jobs(
                resume_path=resume_path,
                index_prefix=index_prefix,
                top_k=top_k,
                constraints_path=constraints_path,
            )
            self._log(f"Top {top_k} results: {json.dumps(results, ensure_ascii=False)}")

            # 4) Personalize
            selected_ids = [r["job_id"] for r in results]
            self._log(f"Personalizing documents for {len(selected_ids)} jobs...")
            out_dir = os.path.abspath(os.path.join(base_dir, cfg["personalized_dir"]))
            cover_path = os.path.abspath(os.path.join(base_dir, cfg["cover_path"]))
            personalize_resume_and_cover_letter(
                resume_tex_path=resume_path,
                cover_letter_tex_path=cover_path,
                jobs_json_path=jobs_path,
                selected_job_ids=selected_ids,
                out_dir=out_dir,
                model=cfg["personalize_model"],
            )

            # Build summary: lookup company/title from jobs file
            with open(jobs_path, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            by_id = {str(j["id"]): j for j in jobs}
            summary = []
            for jid in selected_ids:
                j = by_id.get(str(jid)) or {}
                title = j.get("title") or j.get("details", {}).get("job_title")
                company = j.get("company") or j.get("details", {}).get("organization")
                summary.append({"job_id": jid, "title": title, "company": company})

            self.result_summary = summary
            self._render_summary(summary)
            self._log("Done. Applications listed below.")
        except Exception as e:
            self._log(f"Error: {e}")
            
    def _render_summary(self, items):
        try:
            for iid in self.summary_tree.get_children():
                self.summary_tree.delete(iid)
            for item in items:
                title = item.get("title") or "(No title)"
                company = item.get("company") or "(No company)"
                self.summary_tree.insert('', tk.END, values=(company, title))
            self.summary_count_label.configure(text=f"Applications: {len(items)}")
        except Exception:
            pass


if __name__ == "__main__":
    app = WatMatchUI()
    app.mainloop()

import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import yaml
from dotenv import load_dotenv

# Reuse existing backend functions
from backend.vectorizer import vectorize_jobs
from backend.matcher import match_resume_to_jobs
from backend.scraper import scrape_jobs
from backend.personalizer import personalize_resume_and_cover_letter

# Suppress tokenizer parallelism warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class WatMatchUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WAT-Match Automator")
        self.geometry("900x640")
        self.resizable(True, True)

        # Light theme styling
        self.configure(bg="#ffffff")
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background='#ffffff')
        style.configure('TLabel', background='#ffffff', foreground='#111111')
        style.configure('TButton', padding=8)
        style.configure('Accent.TButton', padding=10, background='#2563eb', foreground='#ffffff')
        style.map('Accent.TButton', background=[('active', '#1d4ed8')])
        style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', foreground='#111111')
        style.configure('Treeview.Heading', font=('Helvetica', 10, 'bold'))

        # Load config
        base_dir = os.path.dirname(__file__)
        self.config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(self.config_path, "r", encoding="utf-8") as cf:
            self.cfg = yaml.safe_load(cf)

        # Load environment variables (e.g., ANTHROPIC_API_KEY)
        load_dotenv()

        # State
        self.run_thread = None
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.result_summary = []

        # UI Elements
        self._build_form()
        # Move actions above log so Start is always visible
        self._build_actions()
        self._build_log()
        self._build_summary_panel()

        # Poll logs
        self.after(100, self._drain_log_queue)

    def _build_form(self):
        form = ttk.Frame(self, padding=12)
        form.pack(fill=tk.X)

        # Max Jobs
        ttk.Label(form, text="Max jobs to scrape:").grid(row=0, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.max_jobs_var = tk.IntVar(value=int(self.cfg.get("max_jobs", 10)))
        self.max_jobs_spin = ttk.Spinbox(form, from_=1, to=10000, textvariable=self.max_jobs_var, width=10)
        self.max_jobs_spin.grid(row=0, column=1, sticky=tk.W, pady=4)

        # Top K
        ttk.Label(form, text="Top K matches:").grid(row=1, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.topk_var = tk.IntVar(value=int(self.cfg.get("top_k", 3)))
        self.topk_spin = ttk.Spinbox(form, from_=1, to=1000, textvariable=self.topk_var, width=10)
        self.topk_spin.grid(row=1, column=1, sticky=tk.W, pady=4)

        # Constraints
        ttk.Label(form, text="Constraints (influences matching):").grid(row=2, column=0, sticky=tk.W, padx=(0,8), pady=4)
        self.constraints_text = scrolledtext.ScrolledText(form, width=60, height=8, wrap=tk.WORD, background="#ffffff", foreground="#111111", insertbackground="#111111")
        self.constraints_text.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E)

        # Prefill constraints from file if set
        constraints_path = self.cfg.get("constraints_path")
        if constraints_path:
            try:
                abs_constraints = os.path.abspath(os.path.join(os.path.dirname(__file__), constraints_path))
                if os.path.exists(abs_constraints):
                    with open(abs_constraints, "r", encoding="utf-8", errors="ignore") as f:
                        self.constraints_text.insert("1.0", f.read())
            except Exception:
                pass

        for i in range(3):
            form.grid_columnconfigure(i, weight=0)

    def _build_log(self):
        frame = ttk.LabelFrame(self, text="Log", padding=8, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,8))
        self.log_area = scrolledtext.ScrolledText(frame, state=tk.DISABLED, width=80, height=16, wrap=tk.WORD, background="#ffffff", foreground="#111111", insertbackground="#111111")
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _build_actions(self):
        bar = ttk.Frame(self, padding=12, style='TFrame')
        bar.pack(fill=tk.X)
        self.start_btn = ttk.Button(bar, text="Start", command=self._on_start, style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT)

    def _build_summary_panel(self):
        frame = ttk.LabelFrame(self, text="Applications", padding=8, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=(0,12))
        self.summary_frame = frame
        columns = ("company", "title")
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=6)
        tree.heading('company', text='Company')
        tree.heading('title', text='Title')
        tree.column('company', width=220, anchor='w')
        tree.column('title', width=520, anchor='w')
        tree.pack(fill=tk.BOTH, expand=True)
        self.summary_tree = tree
        self.summary_count_label = ttk.Label(frame, text="Applications: 0")
        self.summary_count_label.pack(anchor='w', pady=(6,0))

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _drain_log_queue(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_area.configure(state=tk.NORMAL)
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state=tk.DISABLED)
        self.after(100, self._drain_log_queue)

    def _on_start(self):
        if self.run_thread and self.run_thread.is_alive():
            messagebox.showinfo("Busy", "A run is already in progress.")
            return
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.result_summary = []
        # Clear applications panel
        try:
            for iid in self.summary_tree.get_children():
                self.summary_tree.delete(iid)
            self.summary_count_label.configure(text="Applications: 0")
        except Exception:
            pass

        max_jobs = int(self.max_jobs_var.get())
        top_k = int(self.topk_var.get())
        constraints_text = self.constraints_text.get("1.0", tk.END).strip()

        # If missing, inform the user to populate .env, but do not prompt
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            messagebox.showerror("Missing API Key", "Set ANTHROPIC_API_KEY in your .env, then restart.")
            return

        self.run_thread = threading.Thread(target=self._run_pipeline, args=(max_jobs, top_k, constraints_text), daemon=True)
        self.run_thread.start()

    def _run_pipeline(self, max_jobs: int, top_k: int, constraints_text: str):
        try:
            base_dir = os.path.dirname(__file__)
            cfg = self.cfg

            # Write constraints to a temp file alongside configured path, if provided
            constraints_path_cfg = cfg.get("constraints_path")
            constraints_path = None
            if constraints_text:
                if constraints_path_cfg:
                    constraints_path = os.path.abspath(os.path.join(base_dir, constraints_path_cfg))
                else:
                    constraints_path = os.path.join(base_dir, "templates", "constraints.txt")
                os.makedirs(os.path.dirname(constraints_path), exist_ok=True)
                with open(constraints_path, "w", encoding="utf-8") as f:
                    f.write(constraints_text)

            # 1) Scrape
            self._log("Starting scraping session... (browser will open; login then navigate to jobs)")
            jobs_path = scrape_jobs(max_jobs=max_jobs)
            self._log(f"Scraped jobs saved to: {jobs_path}")

            # 2) Vectorize
            self._log("Building/refreshing FAISS index...")
            index_prefix = os.path.abspath(os.path.join(base_dir, cfg["index_prefix"]))
            meta = vectorize_jobs(jobs_json_path=jobs_path, output_prefix=index_prefix, model_name=cfg["embed_model"])
            self._log(f"Index built: {json.dumps({k: meta[k] for k in ['num_vectors','model_name','dim']})}")

            # 3) Match
            self._log("Matching resume to jobs...")
            resume_path = os.path.abspath(os.path.join(base_dir, cfg["resume_path"]))
            results = match_resume_to_jobs(
                resume_path=resume_path,
                index_prefix=index_prefix,
                top_k=top_k,
                constraints_path=constraints_path,
            )
            self._log(f"Top {top_k} results: {json.dumps(results, ensure_ascii=False)}")

            # 4) Personalize
            selected_ids = [r["job_id"] for r in results]
            self._log(f"Personalizing documents for {len(selected_ids)} jobs...")
            out_dir = os.path.abspath(os.path.join(base_dir, cfg["personalized_dir"]))
            cover_path = os.path.abspath(os.path.join(base_dir, cfg["cover_path"]))
            personalize_resume_and_cover_letter(
                resume_tex_path=resume_path,
                cover_letter_tex_path=cover_path,
                jobs_json_path=jobs_path,
                selected_job_ids=selected_ids,
                out_dir=out_dir,
                model=cfg["personalize_model"],
            )

            # Build summary: lookup company/title from jobs file
            with open(jobs_path, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            by_id = {str(j["id"]): j for j in jobs}
            summary = []
            for jid in selected_ids:
                j = by_id.get(str(jid)) or {}
                title = j.get("title") or j.get("details", {}).get("job_title")
                company = j.get("company") or j.get("details", {}).get("organization")
                summary.append({"job_id": jid, "title": title, "company": company})

            self.result_summary = summary
            self._render_summary(summary)
            self._log("Done. Applications listed below.")
        except Exception as e:
            self._log(f"Error: {e}")
            
    def _render_summary(self, items):
        try:
            for iid in self.summary_tree.get_children():
                self.summary_tree.delete(iid)
            for item in items:
                title = item.get("title") or "(No title)"
                company = item.get("company") or "(No company)"
                self.summary_tree.insert('', tk.END, values=(company, title))
            self.summary_count_label.configure(text=f"Applications: {len(items)}")
        except Exception:
            pass


if __name__ == "__main__":
    app = WatMatchUI()
    app.mainloop()