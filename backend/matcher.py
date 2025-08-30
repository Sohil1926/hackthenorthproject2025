# matcher.py (Ultimate Version 4.0 with Domain Analysis)

import fitz
import spacy
import os
import json
from collections import defaultdict

# --- 1. Configuration ---

try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("Downloading 'en_core_web_lg' model for spaCy...")
    os.system("python -m spacy download en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

# --- EXPANDED KNOWLEDGE BASE ---
SKILLS_KNOWLEDGE_BASE = [
    # Programming & Tech
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css", "ruby", "go", "rust", "php", "swift", "kotlin",
    "react", "vue", "angular", "next.js", "node.js", "express.js", "flask", "django", "fastapi", ".net",
    "sql", "postgresql", "mysql", "mongodb", "redis", "nosql", "graphql",
    "git", "github", "gitlab", "docker", "kubernetes", "jenkins", "ci/cd", "terraform",
    "aws", "azure", "gcp", "google cloud", "amazon web services", "cloud",
    "linux", "bash", "powershell", "rest", "api", "apis",
    "data structures", "algorithms", "system design", "software engineering", "computer science",
    # Data Science & Analytics
    "machine learning", "data analysis", "data science", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "ai",
    "analytics", "statistics", "statistical", "tableau", "power bi",
    # Engineering & Hardware
    "electrical engineering", "mechanical engineering", "autocad", "solidworks", "matlab", "circuits", "pcb",
    # Business & Finance
    "supply chain", "logistics", "procurement", "finance", "accounting", "auditing", "investment", "financial analysis",
    "business analysis", "project management", "product management", "agile", "scrum", "jira",
    "marketing", "seo", "sem", "digital transformation", "crm",
    # Security
    "cybersecurity", "security", "networking", "penetration testing", "encryption",
    # Legal
    "law", "legal", "litigation", "contracts", "insolvency", "intellectual property",
    # Soft Skills
    "communication", "teamwork", "problem-solving", "leadership", "analytical", "curiosity"
]

CONCEPT_TO_SKILLS_MAP = {
    "software development": ["python", "java", "c++", "git", "data structures", "algorithms", "system design"],
    "software engineering": ["python", "java", "c++", "git", "data structures", "algorithms", "system design"],
    "computer science": ["python", "java", "c++", "git", "data structures", "algorithms"],
    "developer": ["python", "java", "c++", "git", "data structures", "algorithms"],
    "data science": ["python", "pandas", "numpy", "sql", "machine learning", "data analysis"],
    "data analyst": ["sql", "python", "tableau", "power bi", "data analysis", "analytics"],
    "supply chain": ["supply chain", "logistics", "procurement", "analytics"],
    "digital transformation": ["analytics", "project management", "business analysis"],
    "finance": ["finance", "financial analysis", "accounting"],
    "security": ["cybersecurity", "security", "networking"],
    "law": ["law", "legal", "litigation", "contracts"],
    "engineering": ["mechanical engineering", "electrical engineering", "autocad", "solidworks"]
}

# --- NEW: DOMAIN ANALYSIS CONFIGURATION ---
DOMAIN_KEYWORDS = {
    "Tech": ["python", "java", "c++", "javascript", "react", "sql", "docker", "aws", "machine learning", "data science", "developer", "software engineering", "computer science", "security"],
    "Business": ["supply chain", "finance", "accounting", "marketing", "project management", "business analysis", "digital transformation", "analyst"],
    "Engineering": ["mechanical engineering", "electrical engineering", "autocad", "solidworks", "circuits", "pipelines"],
    "Law": ["law", "legal", "litigation", "contracts"],
    "General": ["communication", "teamwork"] # Fallback domain
}

FIELD_WEIGHTS = {"required_skills": 1.0, "job_title": 0.9, "job_responsibilities": 0.7, "job_summary": 0.5}
CONCEPT_INFERENCE_WEIGHT = 0.8
DOMAIN_MISMATCH_PENALTY = 0.25  # Drastically reduce score if domains don't match
SOFT_SKILL_BONUS = 5  # Add a small bonus up to this max for soft skill matches

class JobMatcher:
    def __init__(self, resume_path):
        self.resume_path = resume_path
        self.resume_text = self._extract_text_from_pdf()
        self.resume_skills = self._extract_terms(self.resume_text, self._initialize_matcher(SKILLS_KNOWLEDGE_BASE))
        self.resume_domain = self._determine_primary_domain(self.resume_skills)
        self.skill_matcher = self._initialize_matcher(SKILLS_KNOWLEDGE_BASE)
        self.concept_matcher = self._initialize_matcher(list(CONCEPT_TO_SKILLS_MAP.keys()))
        print(f"Matcher initialized for {resume_path}. Primary Domain: '{self.resume_domain}'")
        print(f"Found {len(self.resume_skills)} skills: {sorted(list(self.resume_skills))}\n")

    def _initialize_matcher(self, terms):
        matcher = spacy.matcher.PhraseMatcher(nlp.vocab, attr='LOWER')
        patterns = [nlp.make_doc(term) for term in terms]
        matcher.add("MATCHER", patterns)
        return matcher

    def _extract_text_from_pdf(self):
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError(f"The resume file {self.resume_path} was not found.")
        doc = fitz.open(self.resume_path)
        return "".join(page.get_text() for page in doc).lower()

    def _extract_terms(self, text, matcher):
        doc = nlp(text)
        matches = matcher(doc)
        return {doc[start:end].text for _, start, end in matches}

    def _determine_primary_domain(self, skills_set):
        domain_scores = defaultdict(int)
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for skill in skills_set:
                if skill in keywords:
                    domain_scores[domain] += 1
        
        if not domain_scores:
            return "General"
        
        # Prioritize specific domains over General
        if "General" in domain_scores and len(domain_scores) > 1:
            del domain_scores["General"]
            
        return max(domain_scores, key=domain_scores.get)

    def calculate_match(self, job_data):
        job_details = job_data.get('details', {})
        if not job_details or "error" in job_details:
            return {"score": 0, "matched_skills": [], "missing_skills": [], "notes": "Job details missing."}

        weighted_job_skills = defaultdict(float)
        job_text_corpus = ""

        for field, weight in FIELD_WEIGHTS.items():
            field_text = str(job_details.get(field, "")).lower()
            job_text_corpus += field_text + " "
            skills_in_field = self._extract_terms(field_text, self.skill_matcher)
            for skill in skills_in_field:
                weighted_job_skills[skill] = max(weighted_job_skills[skill], weight)

        found_concepts = self._extract_terms(job_text_corpus, self.concept_matcher)
        for concept in found_concepts:
            for skill in CONCEPT_TO_SKILLS_MAP.get(concept, []):
                if weighted_job_skills[skill] < CONCEPT_INFERENCE_WEIGHT:
                    weighted_job_skills[skill] = CONCEPT_INFERENCE_WEIGHT

        if not weighted_job_skills:
            return {"score": 0, "matched_skills": [], "missing_skills": [], "notes": "No relevant skills found."}

        job_skills_set = set(weighted_job_skills.keys())
        job_domain = self._determine_primary_domain(job_skills_set)

        total_job_skill_weight = sum(weighted_job_skills.values())
        matched_skill_weight = sum(weight for skill, weight in weighted_job_skills.items() if skill in self.resume_skills)
        
        score = (matched_skill_weight / total_job_skill_weight) * 100 if total_job_skill_weight > 0 else 0

        # Apply domain mismatch penalty
        if self.resume_domain != "General" and job_domain != "General" and self.resume_domain != job_domain:
            score *= DOMAIN_MISMATCH_PENALTY
            note_suffix = f" (Penalty applied for domain mismatch: Your resume is '{self.resume_domain}', job is '{job_domain}')"
        else:
            note_suffix = ""

        # Apply soft skill bonus
        soft_skills = {"communication", "teamwork", "problem-solving", "leadership", "analytical", "curiosity"}
        matched_soft_skills = len(self.resume_skills.intersection(soft_skills).intersection(job_skills_set))
        bonus = min(matched_soft_skills * 2, SOFT_SKILL_BONUS)
        score = min(100, score + bonus)

        matched_skills = self.resume_skills.intersection(job_skills_set)
        missing_skills = job_skills_set.difference(self.resume_skills)

        return {
            "score": round(score, 2),
            "matched_skills": sorted(list(matched_skills)),
            "missing_skills": sorted(list(missing_skills)),
            "notes": f"Matched {len(matched_skills)} of {len(job_skills_set)} skills." + note_suffix
        }

# --- Example Usage with YOUR provided data ---
if __name__ == "__main__":
    DUMMY_RESUME_PATH = "my_resume.pdf"
    if not os.path.exists(DUMMY_RESUME_PATH):
        print(f"Creating a dummy SOFTWARE DEV resume file: {DUMMY_RESUME_PATH}")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Software Engineer\n"
                                "Skills: Python, Java, C++, SQL, Git, Docker, AWS, REST APIs, System Design.\n"
                                "Strong problem-solving and communication skills.")
        doc.save(DUMMY_RESUME_PATH)
        doc.close()

    matcher = JobMatcher(resume_path=DUMMY_RESUME_PATH)

    jobs = [
        {"id": "432393", "title": "Developer Student", "details": {"job_title": "Developer Student", "job_summary": "Are you a Software Engineering or Computer Science student..."}},
        {"id": "432627", "title": "Senior Supply Chain Analyst - Digital Transformation", "details": {"job_title": "Senior Supply Chain Analyst - Digital Transformation", "job_summary": "passionate about building analytics tools and capabilities... data-focused analytical solutions... supply chain concepts"}},
        {"id": "432517", "title": "Law Student", "details": {"job_title": "Law Student", "job_summary": "exposure to a number of areas of law, including, commercial litigation, insolvency, commercial contracts, procurement, and intellectual property."}}
    ]

    for job in jobs:
        print(f"\n--- Scoring Job: {job['title']} ---")
        match_result = matcher.calculate_match(job)
        print(json.dumps(match_result, indent=2))