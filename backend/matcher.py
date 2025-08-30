import fitz  # This is the PyMuPDF library for some reason
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

# --- 1. Configuration: The Brain's Knowledge Base ---

# Load the spaCy model once
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("Downloading 'en_core_web_lg' model...")
    os.system("python -m spacy download en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

# This is the core "knowledge base" of our matcher.
# The more comprehensive this list, the smarter the agent.
# We use lowercase for consistent matching.
SKILLS_KNOWLEDGE_BASE = [
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css", "ruby", "go",
    "react", "vue", "angular", "next.js", "node.js", "express.js", "flask", "django",
    "sql", "postgresql", "mysql", "mongodb", "redis",
    "git", "github", "gitlab", "docker", "kubernetes", "jenkins", "ci/cd",
    "aws", "azure", "gcp", "google cloud", "amazon web services",
    "linux", "bash", "powershell",
    "machine learning", "data analysis", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "rest", "graphql", "api", "apis",
    "agile", "scrum", "jira"
]

# --- 2. Core Functions ---

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a given PDF file and converts to lowercase."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file {pdf_path} was not found.")
    
    print(f"Reading resume from: {pdf_path}")
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.lower()

def extract_skills(text):
    """
    Extracts predefined skills from a given text using spaCy's phrase matching
    for better accuracy with multi-word skills.
    """
    # Use PhraseMatcher for multi-word skills like "machine learning"
    matcher = spacy.matcher.PhraseMatcher(nlp.vocab, attr='LOWER')
    patterns = [nlp.make_doc(skill) for skill in SKILLS_KNOWLEDGE_BASE]
    matcher.add("SKILL_MATCHER", patterns)

    doc = nlp(text)
    matches = matcher(doc)
    
    found_skills = set()
    for match_id, start, end in matches:
        skill = doc[start:end].text
        found_skills.add(skill)
        
    return list(found_skills)

def calculate_match_score(resume_skills, job_skills):
    """
    Calculates the match score using TF-IDF and Cosine Similarity.
    Returns a score from 0 to 100.
    """
    # If the job requires no specific skills from our list, we can't score it.
    if not job_skills:
        return 0.0

    # If the resume has no skills from our list, the score is 0.
    if not resume_skills:
        return 0.0

    # The vectorizer expects documents (strings), not lists of words.
    resume_text = ' '.join(resume_skills)
    job_text = ' '.join(job_skills)

    # Create a TF-IDF Vectorizer and transform the skill sets
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])

    # Calculate the Cosine Similarity between the two vectors
    # The result is a 2x2 matrix, the value we want is at [0, 1]
    score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    return score * 100

# --- 3. Main Execution Block for Testing ---

if __name__ == "__main__":
    print("--- Running AI Matcher Test ---")

    # Create a dummy resume file for testing
    DUMMY_RESUME_PATH = "dummy_resume.pdf"
    # In a real scenario, you would upload a real resume.
    # For this test, we'll just use plain text.
    # NOTE: This part is just for the test. The function `extract_text_from_pdf` is not used here.
    resume_text_content = """
    Mohammed Elshrief - Software Developer
    A passionate developer with experience in Python, Django, and React.
    Built several projects using PostgreSQL and deployed them on AWS.
    Proficient with Git for version control and Docker for containerization.
    Familiar with agile methodologies.
    """.lower()

    # Example Job Description (from the scraper)
    job_description_text = """
    Job Title: Full Stack Developer
    We are seeking a developer with strong Python and Django skills.
    The ideal candidate will have experience with front-end frameworks like React or Vue.
    Must be comfortable with SQL databases, preferably PostgreSQL.
    Experience with cloud platforms like AWS or GCP is a major plus.
    Knowledge of Docker is required.
    """.lower()

    # --- The Full Process ---
    
    # Step 1: Extract skills from the resume and job description
    print("\n1. Extracting skills...")
    resume_skills = extract_skills(resume_text_content)
    job_skills = extract_skills(job_description_text)

    print(f"\n   [+] Skills found in Resume: {resume_skills}")
    print(f"   [+] Skills required by Job: {job_skills}")

    # Step 2: Calculate the match score
    print("\n2. Calculating match score...")
    match_score = calculate_match_score(resume_skills, job_skills)

    # Step 3: Display the result
    print("\n--- FINAL RESULT ---")
    print(f"The match score is: {match_score:.2f}%")
    print("--------------------")

    # Example of how you would use it with a real PDF
    # print("\n--- Testing with a real PDF (if you have one) ---")
    # try:
    #     # To test this part, create a PDF named 'my_resume.pdf' in the same folder
    #     real_resume_text = extract_text_from_pdf('my_resume.pdf')
    #     real_resume_skills = extract_skills(real_resume_text)
    #     real_score = calculate_match_score(real_resume_skills, job_skills)
    #     print(f"Score with 'my_resume.pdf': {real_score:.2f}%")
    # except FileNotFoundError as e:
    #     print(e)