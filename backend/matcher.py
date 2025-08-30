# matcher.py (Ideal Version 2.0)

import fitz  # PyMuPDF
import spacy
import os
import json
from collections import defaultdict

# --- 1. Configuration ---

# Load the spaCy model once.
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading 'en_core_web_sm' model for spaCy...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# This is the core "knowledge base" of our matcher. It can be expanded over time.
SKILLS_KNOWLEDGE_BASE = [
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css", "ruby", "go", "rust",
    "react", "vue", "angular", "next.js", "node.js", "express.js", "flask", "django", "fastapi",
    "sql", "postgresql", "mysql", "mongodb", "redis", "nosql",
    "git", "github", "gitlab", "docker", "kubernetes", "jenkins", "ci/cd", "terraform",
    "aws", "azure", "gcp", "google cloud", "amazon web services", "cloud",
    "linux", "bash", "powershell",
    "machine learning", "data analysis", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "ai",
    "rest", "graphql", "api", "apis",
    "agile", "scrum", "jira", "figma", "selenium", "playwright",
    "data structures", "algorithms", "system design"
]

# --- WEIGHTING CONFIGURATION ---
# This is the secret sauce. We value skills found in certain fields more than others.
FIELD_WEIGHTS = {
    "required_skills": 1.0,
    "job_title": 0.9,
    "job_responsibilities": 0.7,
    "job_summary": 0.5,
    "targeted_degrees_and_disciplines": 0.4,
}


class JobMatcher:
    """
    An intelligent job matcher that scores jobs against a user's profile
    using a weighted analysis of structured job data.
    """
    def __init__(self, resume_path):
        self.resume_path = resume_path
        self.skill_matcher = self._initialize_skill_matcher()
        self.resume_skills = self._parse_resume()
        print(f"Matcher initialized for {resume_path}.")
        print(f"Found {len(self.resume_skills)} unique skills in resume: {sorted(list(self.resume_skills))}\n")

    def _initialize_skill_matcher(self):
        """Initializes spaCy's PhraseMatcher for efficient skill finding."""
        matcher = spacy.matcher.PhraseMatcher(nlp.vocab, attr='LOWER')
        patterns = [nlp.make_doc(skill) for skill in SKILLS_KNOWLEDGE_BASE]
        matcher.add("SKILL_MATCHER", patterns)
        return matcher

    def _extract_text_from_pdf(self):
        """Extracts all text from the resume PDF and converts to lowercase."""
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError(f"The resume file {self.resume_path} was not found.")
        
        doc = fitz.open(self.resume_path)
        text = "".join(page.get_text() for page in doc)
        return text.lower()

    def _extract_skills(self, text):
        """Extracts a set of skills from a given text."""
        doc = nlp(text)
        matches = self.skill_matcher(doc)
        return {doc[start:end].text for _, start, end in matches}

    def _parse_resume(self):
        """Processes the resume to extract and store its skills."""
        resume_text = self._extract_text_from_pdf()
        return self._extract_skills(resume_text)

    def calculate_match(self, job_data):
        """
        Calculates a detailed match score for a single job.
        
        Returns:
            dict: A dictionary containing the score and a breakdown of the match.
        """
        job_details = job_data.get('details', {})
        if not job_details or "error" in job_details:
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "notes": "Job details were missing or contained an error."
            }

        # --- Weighted Skill Extraction from Job ---
        weighted_job_skills = defaultdict(float)
        total_job_skill_weight = 0

        for field, weight in FIELD_WEIGHTS.items():
            field_text = str(job_details.get(field, "")).lower()
            skills_in_field = self._extract_skills(field_text)
            
            for skill in skills_in_field:
                # We take the highest weight if a skill appears in multiple fields
                weighted_job_skills[skill] = max(weighted_job_skills[skill], weight)

        if not weighted_job_skills:
            return {
                "score": 0,
                "matched_skills": sorted(list(self.resume_skills)),
                "missing_skills": [],
                "notes": "No relevant skills found in the job description."
            }

        # --- Scoring Logic ---
        matched_skill_weight = 0
        
        for skill, weight in weighted_job_skills.items():
            total_job_skill_weight += weight
            if skill in self.resume_skills:
                matched_skill_weight += weight

        # The score is the ratio of matched weight to total possible weight.
        score = (matched_skill_weight / total_job_skill_weight) * 100 if total_job_skill_weight > 0 else 0

        # --- Breakdown Analysis ---
        job_skills_set = set(weighted_job_skills.keys())
        matched_skills = self.resume_skills.intersection(job_skills_set)
        missing_skills = job_skills_set.difference(self.resume_skills)

        return {
            "score": round(score, 2),
            "matched_skills": sorted(list(matched_skills)),
            "missing_skills": sorted(list(missing_skills)),
            "notes": f"Matched {len(matched_skills)} of {len(job_skills_set)} required skills."
        }


# --- Example Usage ---
if __name__ == "__main__":
    # Create a dummy resume file for testing if it doesn't exist
    DUMMY_RESUME_PATH = "my_resume.pdf"
    if not os.path.exists(DUMMY_RESUME_PATH):
        print(f"Creating a dummy resume file: {DUMMY_RESUME_PATH}")
        # This is a very basic way to create a PDF, good enough for text extraction
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Mohammed Elshrief - Software Developer\n"
                                  "Experienced in Python, Django, and React.\n"
                                  "Built several projects using PostgreSQL and deployed them on AWS.\n"
                                  "Proficient with Git for version control and Docker for containerization.\n"
                                  "Familiar with agile methodologies and system design principles.")
        doc.save(DUMMY_RESUME_PATH)
        doc.close()

    # 1. Initialize the matcher with your resume
    try:
        matcher = JobMatcher(resume_path=DUMMY_RESUME_PATH)
    except FileNotFoundError as e:
        print(e)
        exit()

    # 2. Create some sample job data (mimicking your scraper's output)
    sample_job_1 = {
        "id": "12345",
        "title": "Senior Python Developer",
        "company": "Tech Solutions Inc.",
        "details": {
            "job_title": "Senior Python Developer",
            "required_skills": "Must have strong experience in Python, Django, and REST APIs. Knowledge of Docker is required.",
            "job_summary": "We are looking for a Python developer to join our team. You will work with React on the frontend.",
            "job_responsibilities": "Design and implement backend services. Deploy applications using AWS."
        }
    }

    sample_job_2 = {
        "id": "67890",
        "title": "Frontend Developer (Java)",
        "company": "Creative Designs",
        "details": {
            "job_title": "Frontend Developer",
            "required_skills": "Expertise in Java and Spring Boot is essential. Experience with Angular is a plus.",
            "job_summary": "This role focuses on building user interfaces. Some Python scripting may be involved for automation."
        }
    }

    # 3. Calculate the match for each job
    print("\n--- Scoring Job 1: Senior Python Developer ---")
    match_result_1 = matcher.calculate_match(sample_job_1)
    print(json.dumps(match_result_1, indent=2))

    print("\n--- Scoring Job 2: Frontend Developer (Java) ---")
    match_result_2 = matcher.calculate_match(sample_job_2)
    print(json.dumps(match_result_2, indent=2))