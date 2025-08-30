# matcher.py (Ultimate Version 5.0 - Production Ready)

import fitz
import spacy
import os
import json
import re
from collections import defaultdict
from typing import Dict, Set, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 1. Configuration ---

def load_spacy_model():
    """Load spaCy model with automatic download if needed."""
    model_name = "en_core_web_lg"
    try:
        return spacy.load(model_name)
    except OSError:
        logger.info(f"Downloading '{model_name}' model for spaCy...")
        os.system(f"python -m spacy download {model_name}")
        return spacy.load(model_name)

nlp = load_spacy_model()

# --- EXPANDED KNOWLEDGE BASE ---
SKILLS_KNOWLEDGE_BASE = {
    # Programming Languages
    "programming": [
        "python", "java", "c++", "c#", "javascript", "typescript", "ruby", "go", "golang",
        "rust", "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "bash", "shell",
        "objective-c", "visual basic", "vb.net", "fortran", "cobol", "lua", "dart"
    ],
    
    # Web Technologies
    "web": [
        "html", "html5", "css", "css3", "sass", "less", "bootstrap", "tailwind",
        "react", "react.js", "vue", "vue.js", "angular", "angularjs", "next.js", "nuxt.js",
        "svelte", "ember", "backbone", "jquery", "webpack", "babel", "vite"
    ],
    
    # Backend & Frameworks
    "backend": [
        "node.js", "nodejs", "express", "express.js", "flask", "django", "fastapi",
        "spring", "spring boot", ".net", "asp.net", "rails", "ruby on rails",
        "laravel", "symfony", "gin", "echo", "fiber", "actix"
    ],
    
    # Databases
    "database": [
        "sql", "nosql", "postgresql", "postgres", "mysql", "mariadb", "oracle",
        "sql server", "mongodb", "cassandra", "redis", "elasticsearch", "dynamodb",
        "firestore", "firebase", "neo4j", "graphql", "prisma", "sequelize",
        "database design", "data modeling", "indexing", "query optimization"
    ],
    
    # DevOps & Cloud
    "devops": [
        "docker", "kubernetes", "k8s", "jenkins", "github actions", "gitlab ci",
        "ci/cd", "continuous integration", "continuous deployment", "terraform",
        "ansible", "puppet", "chef", "helm", "argocd", "prometheus", "grafana",
        "elk stack", "datadog", "new relic"
    ],
    
    "cloud": [
        "aws", "amazon web services", "ec2", "s3", "lambda", "rds", "dynamodb",
        "azure", "microsoft azure", "gcp", "google cloud platform", "google cloud",
        "cloud computing", "serverless", "microservices", "cloud architecture",
        "cloud native", "paas", "iaas", "saas"
    ],
    
    # Data Science & AI
    "data_science": [
        "machine learning", "deep learning", "artificial intelligence", "ai", "ml",
        "data science", "data analysis", "data analytics", "statistics", "statistical analysis",
        "pandas", "numpy", "scipy", "scikit-learn", "sklearn", "tensorflow", "pytorch",
        "keras", "xgboost", "lightgbm", "nlp", "natural language processing",
        "computer vision", "opencv", "neural networks", "random forest", "svm"
    ],
    
    # Business Intelligence
    "business_intelligence": [
        "tableau", "power bi", "looker", "qlik", "data visualization", "dashboards",
        "reporting", "etl", "data warehousing", "business intelligence", "bi"
    ],
    
    # Mobile Development
    "mobile": [
        "ios", "android", "react native", "flutter", "xamarin", "swift", "swiftui",
        "kotlin", "java", "mobile development", "app development"
    ],
    
    # Testing & QA
    "testing": [
        "unit testing", "integration testing", "test automation", "selenium",
        "cypress", "jest", "mocha", "pytest", "junit", "testng", "cucumber",
        "qa", "quality assurance", "test driven development", "tdd", "bdd"
    ],
    
    # Security
    "security": [
        "cybersecurity", "information security", "network security", "application security",
        "penetration testing", "ethical hacking", "vulnerability assessment", "siem",
        "firewall", "ids", "ips", "encryption", "ssl", "tls", "oauth", "jwt",
        "security auditing", "compliance", "gdpr", "pci dss", "iso 27001"
    ],
    
    # Version Control & Collaboration
    "version_control": [
        "git", "github", "gitlab", "bitbucket", "svn", "mercurial", "perforce",
        "version control", "source control", "branching", "merging", "pull requests"
    ],
    
    # Project Management & Methodologies
    "project_management": [
        "agile", "scrum", "kanban", "waterfall", "project management", "product management",
        "jira", "confluence", "trello", "asana", "monday.com", "sprint planning",
        "backlog", "user stories", "epics", "roadmap", "stakeholder management"
    ],
    
    # Business & Finance
    "business": [
        "business analysis", "business development", "strategy", "consulting",
        "market research", "competitive analysis", "swot analysis", "roi analysis",
        "kpi", "okr", "business process", "process improvement", "six sigma", "lean"
    ],
    
    "finance": [
        "finance", "accounting", "financial analysis", "financial modeling",
        "budgeting", "forecasting", "valuation", "investment", "portfolio management",
        "risk management", "audit", "tax", "gaap", "ifrs", "excel", "financial reporting"
    ],
    
    # Marketing & Sales
    "marketing": [
        "marketing", "digital marketing", "seo", "sem", "ppc", "google ads",
        "facebook ads", "social media marketing", "content marketing", "email marketing",
        "marketing automation", "hubspot", "salesforce", "crm", "lead generation"
    ],
    
    # Supply Chain & Operations
    "supply_chain": [
        "supply chain", "logistics", "procurement", "inventory management",
        "warehouse management", "transportation", "distribution", "erp", "sap",
        "oracle scm", "demand planning", "forecasting", "vendor management"
    ],
    
    # Engineering & Hardware
    "engineering": [
        "mechanical engineering", "electrical engineering", "civil engineering",
        "chemical engineering", "biomedical engineering", "industrial engineering",
        "systems engineering", "quality engineering"
    ],
    
    "hardware": [
        "autocad", "solidworks", "catia", "ansys", "matlab", "simulink",
        "labview", "pcb design", "fpga", "vhdl", "verilog", "embedded systems",
        "microcontrollers", "arduino", "raspberry pi", "plc", "scada"
    ],
    
    # Legal
    "legal": [
        "law", "legal", "litigation", "contracts", "intellectual property",
        "patent", "trademark", "copyright", "compliance", "regulatory", "gdpr",
        "corporate law", "employment law", "real estate law", "tax law"
    ],
    
    # Soft Skills
    "soft_skills": [
        "communication", "teamwork", "collaboration", "problem-solving", "critical thinking",
        "leadership", "management", "analytical", "creativity", "innovation",
        "time management", "organization", "attention to detail", "adaptability",
        "flexibility", "initiative", "self-motivated", "customer service", "presentation",
        "negotiation", "conflict resolution", "decision making", "strategic thinking"
    ],
    
    # Industry Specific
    "healthcare": [
        "healthcare", "medical", "clinical", "patient care", "hipaa", "ehr", "emr",
        "medical devices", "pharmaceutical", "biotech", "clinical trials", "fda"
    ],
    
    "education": [
        "teaching", "curriculum development", "instructional design", "e-learning",
        "lms", "educational technology", "assessment", "pedagogy"
    ]
}

# Flatten skills for matching
FLAT_SKILLS_LIST = []
for category, skills in SKILLS_KNOWLEDGE_BASE.items():
    FLAT_SKILLS_LIST.extend(skills)

# Enhanced concept mapping with more granular mappings
CONCEPT_TO_SKILLS_MAP = {
    # Job titles and roles
    "software developer": ["python", "java", "javascript", "git", "sql", "api", "testing"],
    "software engineer": ["python", "java", "c++", "git", "system design", "algorithms", "data structures"],
    "full stack developer": ["javascript", "react", "node.js", "sql", "html", "css", "api"],
    "frontend developer": ["javascript", "react", "vue", "angular", "html", "css", "responsive design"],
    "backend developer": ["python", "java", "node.js", "sql", "api", "microservices", "database design"],
    "data scientist": ["python", "machine learning", "pandas", "numpy", "sql", "statistics", "tensorflow"],
    "data analyst": ["sql", "python", "tableau", "power bi", "excel", "data analysis", "reporting"],
    "data engineer": ["python", "sql", "etl", "spark", "airflow", "data warehousing", "cloud"],
    "devops engineer": ["docker", "kubernetes", "jenkins", "terraform", "aws", "ci/cd", "linux"],
    "cloud engineer": ["aws", "azure", "terraform", "docker", "kubernetes", "cloud architecture"],
    "machine learning engineer": ["python", "tensorflow", "pytorch", "machine learning", "deep learning"],
    "mobile developer": ["swift", "kotlin", "react native", "flutter", "ios", "android"],
    "qa engineer": ["testing", "selenium", "automation", "qa", "test cases", "bug tracking"],
    "security engineer": ["cybersecurity", "penetration testing", "firewall", "encryption", "vulnerability assessment"],
    "business analyst": ["business analysis", "requirements gathering", "stakeholder management", "process improvement"],
    "project manager": ["project management", "agile", "scrum", "jira", "stakeholder management"],
    "product manager": ["product management", "roadmap", "user stories", "market research", "analytics"],
    
    # General concepts
    "web development": ["html", "css", "javascript", "react", "api", "responsive design"],
    "programming": ["python", "java", "c++", "algorithms", "data structures", "git"],
    "database": ["sql", "database design", "postgresql", "mysql", "mongodb"],
    "automation": ["python", "selenium", "jenkins", "automation", "scripting"],
    "analytics": ["data analysis", "statistics", "visualization", "reporting", "excel"],
    "infrastructure": ["docker", "kubernetes", "terraform", "cloud", "networking"],
    "artificial intelligence": ["machine learning", "deep learning", "neural networks", "nlp", "computer vision"]
}

# Domain keywords with weighted importance
DOMAIN_KEYWORDS = {
    "Tech": {
        "primary": ["software", "developer", "engineer", "programming", "coding", "technical"],
        "secondary": ["python", "java", "javascript", "sql", "api", "cloud", "data"]
    },
    "Data": {
        "primary": ["data", "analytics", "analysis", "machine learning", "ai", "statistics"],
        "secondary": ["pandas", "numpy", "tableau", "power bi", "etl", "visualization"]
    },
    "Business": {
        "primary": ["business", "management", "strategy", "consulting", "analyst"],
        "secondary": ["finance", "marketing", "operations", "supply chain", "project management"]
    },
    "Engineering": {
        "primary": ["engineering", "mechanical", "electrical", "civil", "chemical"],
        "secondary": ["autocad", "solidworks", "matlab", "design", "manufacturing"]
    },
    "Security": {
        "primary": ["security", "cybersecurity", "information security"],
        "secondary": ["penetration testing", "vulnerability", "firewall", "compliance"]
    },
    "Legal": {
        "primary": ["law", "legal", "attorney", "lawyer", "paralegal"],
        "secondary": ["litigation", "contracts", "compliance", "regulatory"]
    },
    "Healthcare": {
        "primary": ["healthcare", "medical", "clinical", "health"],
        "secondary": ["patient", "hospital", "pharmaceutical", "biotech"]
    }
}

# Scoring configuration
FIELD_WEIGHTS = {
    "required_skills": 1.0,
    "job_title": 0.9,
    "job_responsibilities": 0.8,
    "job_summary": 0.6,
    "job_description": 0.7,
    "additional_information": 0.4
}

SCORING_CONFIG = {
    "concept_inference_weight": 0.7,
    "domain_mismatch_penalty": 0.3,  # Less harsh penalty
    "soft_skill_bonus_max": 10,
    "soft_skill_bonus_per_match": 2,
    "exact_match_bonus": 1.2,  # Bonus for exact skill matches
    "partial_match_weight": 0.5,  # Weight for partial/related skill matches
    "experience_level_mismatch_penalty": 0.8  # Penalty for junior applying to senior roles
}

class JobMatcher:
    def __init__(self, resume_path: str):
        """Initialize the job matcher with a resume."""
        self.resume_path = resume_path
        self.resume_text = self._extract_text_from_pdf()
        self.resume_doc = nlp(self.resume_text)
        
        # Initialize matchers
        self.skill_matcher = self._initialize_matcher(FLAT_SKILLS_LIST)
        self.concept_matcher = self._initialize_matcher(list(CONCEPT_TO_SKILLS_MAP.keys()))
        
        # Extract resume information
        self.resume_skills = self._extract_skills_from_resume()
        self.resume_concepts = self._extract_concepts_from_resume()
        self.resume_domains = self._determine_domains(self.resume_skills, self.resume_text)
        self.experience_level = self._detect_experience_level()
        
        logger.info(f"Matcher initialized for {resume_path}")
        logger.info(f"Primary Domains: {self.resume_domains[:2]}")
        logger.info(f"Found {len(self.resume_skills)} skills")
        logger.info(f"Experience Level: {self.experience_level}")

    def _initialize_matcher(self, terms: List[str]) -> spacy.matcher.PhraseMatcher:
        """Initialize a spaCy PhraseMatcher with given terms."""
        matcher = spacy.matcher.PhraseMatcher(nlp.vocab, attr='LOWER')
        patterns = [nlp.make_doc(term.lower()) for term in terms]
        matcher.add("MATCHER", patterns)
        return matcher

    def _extract_text_from_pdf(self) -> str:
        """Extract text from PDF resume."""
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError(f"Resume file {self.resume_path} not found.")
        
        try:
            doc = fitz.open(self.resume_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.lower()
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            raise

    def _extract_skills_from_resume(self) -> Set[str]:
        """Extract skills from resume using multiple methods."""
        skills = set()
        
        # Method 1: Direct matching using PhraseMatcher
        matches = self.skill_matcher(self.resume_doc)
        for _, start, end in matches:
            skill = self.resume_doc[start:end].text
            skills.add(skill)
        
        # Method 2: Look for skills in common resume sections
        skill_sections = ["skills", "technical skills", "technologies", "tools", "competencies"]
        lines = self.resume_text.split('\n')
        in_skill_section = False
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if we're entering a skills section
            if any(section in line_lower for section in skill_sections):
                in_skill_section = True
                continue
            
            # Check if we're leaving the skills section
            if in_skill_section and line_lower and not any(c in line_lower for c in [',', '•', '|', ';']):
                if len(line_lower.split()) > 5:  # Likely a new section
                    in_skill_section = False
            
            # Extract skills from skill section
            if in_skill_section:
                # Split by common delimiters
                potential_skills = re.split(r'[,;|•\t]+', line_lower)
                for potential_skill in potential_skills:
                    skill = potential_skill.strip()
                    if skill in FLAT_SKILLS_LIST:
                        skills.add(skill)
        
        return skills

    def _extract_concepts_from_resume(self) -> Set[str]:
        """Extract high-level concepts from resume."""
        matches = self.concept_matcher(self.resume_doc)
        return {self.resume_doc[start:end].text for _, start, end in matches}

    def _determine_domains(self, skills: Set[str], text: str) -> List[str]:
        """Determine the primary domains of the resume."""
        domain_scores = defaultdict(float)
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            # Check primary keywords (higher weight)
            for keyword in keywords.get("primary", []):
                if keyword in text:
                    domain_scores[domain] += 2.0
            
            # Check secondary keywords
            for keyword in keywords.get("secondary", []):
                if keyword in text:
                    domain_scores[domain] += 1.0
            
            # Check skills
            for skill in skills:
                if skill in keywords.get("secondary", []):
                    domain_scores[domain] += 0.5
        
        # Sort domains by score
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        return [domain for domain, _ in sorted_domains if _ > 0]

    def _detect_experience_level(self) -> str:
        """Detect the experience level from resume."""
        text_lower = self.resume_text.lower()
        
        # Look for experience indicators
        senior_indicators = ["senior", "lead", "principal", "staff", "architect", "manager", "director", "10+ years", "15+ years"]
        mid_indicators = ["5+ years", "3-5 years", "mid-level", "intermediate"]
        junior_indicators = ["junior", "entry level", "intern", "co-op", "student", "recent graduate", "0-2 years"]
        
        for indicator in senior_indicators:
            if indicator in text_lower:
                return "senior"
        
        for indicator in mid_indicators:
            if indicator in text_lower:
                return "mid"
        
        for indicator in junior_indicators:
            if indicator in text_lower:
                return "junior"
        
        return "unknown"

    def _extract_job_skills(self, job_details: Dict) -> Dict[str, float]:
        """Extract skills from job posting with weights."""
        weighted_skills = defaultdict(float)
        
        for field, weight in FIELD_WEIGHTS.items():
            field_text = str(job_details.get(field, "")).lower()
            if not field_text:
                continue
            
            # Extract direct skill matches
            doc = nlp(field_text)
            matches = self.skill_matcher(doc)
            for _, start, end in matches:
                skill = doc[start:end].text
                weighted_skills[skill] = max(weighted_skills[skill], weight)
            
            # Extract concepts and infer skills
            concept_matches = self.concept_matcher(doc)
            for _, start, end in concept_matches:
                concept = doc[start:end].text
                for inferred_skill in CONCEPT_TO_SKILLS_MAP.get(concept, []):
                    if inferred_skill in FLAT_SKILLS_LIST:
                        inferred_weight = weight * SCORING_CONFIG["concept_inference_weight"]
                        weighted_skills[inferred_skill] = max(weighted_skills[inferred_skill], inferred_weight)
        
        return weighted_skills

    def _calculate_skill_match_score(self, job_skills: Dict[str, float]) -> Tuple[float, Set[str], Set[str]]:
        """Calculate skill matching score."""
        if not job_skills:
            return 0.0, set(), set()
        
        matched_skills = set()
        matched_weight = 0.0
        total_weight = sum(job_skills.values())
        
        for skill, weight in job_skills.items():
            if skill in self.resume_skills:
                matched_skills.add(skill)
                matched_weight += weight * SCORING_CONFIG["exact_match_bonus"]
            # Check for partial matches (e.g., "react" matches "react.js")
            elif any(resume_skill in skill or skill in resume_skill for resume_skill in self.resume_skills):
                matched_skills.add(skill)
                matched_weight += weight * SCORING_CONFIG["partial_match_weight"]
        
        missing_skills = set(job_skills.keys()) - matched_skills
        base_score = (matched_weight / total_weight * 100) if total_weight > 0 else 0
        
        return base_score, matched_skills, missing_skills

    def _apply_modifiers(self, base_score: float, job_details: Dict, job_skills: Set[str]) -> Tuple[float, List[str]]:
        """Apply score modifiers based on various factors."""
        score = base_score
        notes = []
        
        # Domain matching
        job_text = " ".join(str(v).lower() for v in job_details.values() if v)
        job_domains = self._determine_domains(job_skills, job_text)
        
        if self.resume_domains and job_domains:
            if self.resume_domains[0] == job_domains[0]:
                score *= 1.1  # Bonus for exact domain match
                notes.append(f"Domain match: {self.resume_domains[0]}")
            elif any(domain in job_domains[:2] for domain in self.resume_domains[:2]):
                score *= 1.05  # Small bonus for secondary domain match
            elif not any(domain in job_domains for domain in self.resume_domains):
                score *= (1 - SCORING_CONFIG["domain_mismatch_penalty"])
                notes.append(f"Domain mismatch: Resume={self.resume_domains[0]}, Job={job_domains[0]}")
        
        # Experience level matching
        job_title = job_details.get("job_title", "").lower()
        if "senior" in job_title and self.experience_level == "junior":
            score *= SCORING_CONFIG["experience_level_mismatch_penalty"]
            notes.append("Experience level mismatch (Junior applying to Senior role)")
        elif "junior" in job_title and self.experience_level == "senior":
            notes.append("Potentially overqualified")
        
        # Soft skills bonus
        soft_skills_in_job = job_skills.intersection(SKILLS_KNOWLEDGE_BASE["soft_skills"])
        soft_skills_matched = self.resume_skills.intersection(soft_skills_in_job)
        soft_bonus = min(
            len(soft_skills_matched) * SCORING_CONFIG["soft_skill_bonus_per_match"],
            SCORING_CONFIG["soft_skill_bonus_max"]
        )
        score += soft_bonus
        
        if soft_skills_matched:
            notes.append(f"Soft skills matched: {len(soft_skills_matched)}")
        
        return min(100, score), notes

    def calculate_match(self, job_data: Dict) -> Dict:
        """Calculate match score for a job posting."""
        job_details = job_data.get('details', {})
        
        # Check for valid job details
        if not job_details or "error" in job_details:
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "critical_missing": [],
                "nice_to_have_missing": [],
                "domains": [],
                "notes": "Job details missing or error in data."
            }
        
        try:
            # Extract skills from job
            weighted_job_skills = self._extract_job_skills(job_details)
            job_skills_set = set(weighted_job_skills.keys())
            
            # Calculate base score
            base_score, matched_skills, missing_skills = self._calculate_skill_match_score(weighted_job_skills)
            
            # Apply modifiers
            final_score, notes = self._apply_modifiers(base_score, job_details, job_skills_set)
            
            # Categorize missing skills
            critical_missing = []
            nice_to_have_missing = []
            
            for skill in missing_skills:
                if weighted_job_skills[skill] >= 0.8:  # High weight = critical
                    critical_missing.append(skill)
                else:
                    nice_to_have_missing.append(skill)
            
            # Get job domains
            job_text = " ".join(str(v).lower() for v in job_details.values() if v)
            job_domains = self._determine_domains(job_skills_set, job_text)
            
            # Compile final notes
            final_notes = f"Matched {len(matched_skills)}/{len(job_skills_set)} skills"
            if notes:
                final_notes += ". " + ". ".join(notes)
            
            return {
                "score": round(final_score, 2),
                "matched_skills": sorted(list(matched_skills)),
                "missing_skills": sorted(list(missing_skills)),
                "critical_missing": sorted(critical_missing),
                "nice_to_have_missing": sorted(nice_to_have_missing),
                "domains": job_domains[:2],  # Top 2 domains
                "confidence": "high" if final_score > 70 else "medium" if final_score > 40 else "low",
                "notes": final_notes
            }
            
        except Exception as e:
            logger.error(f"Error calculating match: {e}")
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "critical_missing": [],
                "nice_to_have_missing": [],
                "domains": [],
                "notes": f"Error calculating match: {str(e)}"
            }

    def get_recommendations(self, match_result: Dict) -> List[str]:
        """Generate recommendations based on match results."""
        recommendations = []
        score = match_result.get("score", 0)
        critical_missing = match_result.get("critical_missing", [])
        
        if score >= 70:
            recommendations.append("Strong match! Consider applying with confidence.")
            if critical_missing:
                recommendations.append(f"Consider highlighting transferable skills related to: {', '.join(critical_missing[:3])}")
        elif score >= 40:
            recommendations.append("Moderate match. Consider applying if you're interested.")
            if critical_missing:
                recommendations.append(f"Priority skills to develop: {', '.join(critical_missing[:3])}")
        else:
            recommendations.append("Low match. Consider gaining more relevant experience first.")
            if critical_missing:
                recommendations.append(f"Key skills gap: {', '.join(critical_missing[:5])}")
        
        return recommendations


# --- Example Usage ---
if __name__ == "__main__":
    # Create dummy resume for testing
    DUMMY_RESUME_PATH = "my_resume.pdf"
    if not os.path.exists(DUMMY_RESUME_PATH):
        print(f"Creating a dummy resume file: {DUMMY_RESUME_PATH}")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), 
            "John Doe - Software Engineer\n\n"
            "EXPERIENCE:\n"
            "Software Developer at Tech Corp (3 years)\n"
            "- Developed web applications using React and Node.js\n"
            "- Implemented RESTful APIs and microservices\n\n"
            "SKILLS:\n"
            "Programming: Python, JavaScript, Java, SQL\n"
            "Web: React, Node.js, HTML, CSS, REST APIs\n"
            "Tools: Git, Docker, AWS, Jenkins, Jira\n"
            "Databases: PostgreSQL, MongoDB, Redis\n"
            "Other: Agile, Problem-solving, Communication, Team collaboration\n\n"
            "EDUCATION:\n"
            "Bachelor of Computer Science"
        )
        doc.save(DUMMY_RESUME_PATH)
        doc.close()

    # Initialize matcher
    matcher = JobMatcher(resume_path=DUMMY_RESUME_PATH)

    # Test with sample jobs
    jobs = [
        {
            "id": "432393",
            "title": "Full Stack Developer",
            "details": {
                "job_title": "Full Stack Developer",
                "job_summary": "Looking for a full stack developer with React and Node.js experience",
                "required_skills": "JavaScript, React, Node.js, SQL, Git, REST APIs",
                "job_responsibilities": "Develop and maintain web applications, create APIs, collaborate with team"
            }
        },
        {
            "id": "432627",
            "title": "Data Scientist",
            "details": {
                "job_title": "Data Scientist",
                "job_summary": "Seeking data scientist for machine learning projects",
                "required_skills": "Python, Machine Learning, TensorFlow, Statistics, SQL",
                "job_responsibilities": "Build ML models, analyze data, create visualizations"
            }
        },
        {
            "id": "432517",
            "title": "DevOps Engineer",
            "details": {
                "job_title": "DevOps Engineer",
                "job_summary": "DevOps engineer for cloud infrastructure",
                "required_skills": "Docker, Kubernetes, AWS, Terraform, CI/CD, Jenkins",
                "job_responsibilities": "Manage cloud infrastructure, implement CI/CD pipelines"
            }
        }
    ]

    print("\n" + "="*80)
    for job in jobs:
        print(f"\n--- Analyzing: {job['title']} (ID: {job['id']}) ---")
        match_result = matcher.calculate_match(job)
        
        print(f"Score: {match_result['score']}% ({match_result['confidence']} confidence)")
        print(f"Domains: {', '.join(match_result['domains'])}")
        print(f"Matched Skills: {', '.join(match_result['matched_skills'][:5])}")
        if match_result['critical_missing']:
            print(f"Critical Missing: {', '.join(match_result['critical_missing'][:3])}")
        print(f"Notes: {match_result['notes']}")
        
        # Get recommendations
        recommendations = matcher.get_recommendations(match_result)
        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
    
    print("\n" + "="*80)