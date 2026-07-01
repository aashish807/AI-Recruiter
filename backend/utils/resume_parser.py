import json
import os
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from models.resume import CandidateParsedProfile, ExperienceSchema, ProjectSchema
from .parser import extract_text

# Load the prompt template
PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "resume_parsing.txt")

def _get_llm():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    return ChatOpenAI(model="gpt-4o", temperature=0)

def _safe_loads(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback regex extraction of JSON structure
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

def parse_locally(text: str) -> Dict[str, Any]:
    """Heuristic fallback extraction when OpenAI key is missing."""
    profile = {
        "name": "Anonymized Candidate",
        "email": None,
        "phone": None,
        "education": [],
        "skills": [],
        "experience": [],
        "companies": [],
        "projects": [],
        "certifications": [],
        "awards": [],
        "publications": [],
        "technologies": [],
        "languages": [],
        "soft_skills": [],
        "leadership": [],
        "responsibilities": [],
        "years_of_experience": 0.0
    }

    # Extract email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_match:
        profile["email"] = email_match.group(0)

    # Extract phone
    phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_match:
        profile["phone"] = phone_match.group(0)

    # Guess Name from first line if it's not email/phone
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first_line = lines[0]
        if "@" not in first_line and len(first_line) < 50:
            profile["name"] = first_line

    # Simple skills keyword extraction
    keywords = ["python", "fastapi", "aws", "docker", "kubernetes", "java", "spring boot", "react", "javascript", "sql", "go", "devops"]
    found_skills = []
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text.lower()):
            found_skills.append(kw.title() if kw != "sql" else "SQL")
    profile["skills"] = found_skills
    profile["technologies"] = found_skills

    # Estimate experience years
    exp_matches = re.findall(r"(\d+(?:\.\d+)?)\s*years?\b", text.lower())
    if exp_matches:
        try:
            profile["years_of_experience"] = max(float(x) for x in exp_matches)
        except ValueError:
            pass

    # Create one mock experience record if years > 0
    if profile["years_of_experience"] > 0:
        profile["experience"].append({
            "company": "Previous Employer",
            "role": "Software Engineer",
            "start_date": "N/A",
            "end_date": "Present",
            "description": f"Worked as a developer. Resume parsed locally with heuristic matching. Extracted keywords: {', '.join(found_skills)}"
        })

    # Project heuristic extraction
    projects = []
    text_lines = text.split("\n")
    in_projects_section = False
    
    for line in text_lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        line_lower = line_strip.lower()
        if any(section in line_lower for section in ["experience:", "education:", "skills:", "summary:", "about the role:"]):
            in_projects_section = False
            
        if "projects:" in line_lower or line_lower == "projects":
            in_projects_section = True
            continue
            
        if in_projects_section:
            if line_strip.startswith("-") or line_strip.startswith("*"):
                proj_line = re.sub(r"^[-*\s]+", "", line_strip)
                if ":" in proj_line:
                    title, desc = proj_line.split(":", 1)
                    title = title.strip()
                    desc = desc.strip()
                else:
                    title = proj_line.strip()
                    desc = "Portfolio project implementation"
                
                proj_tech = []
                for kw in keywords:
                    if re.search(rf"\b{re.escape(kw)}\b", desc.lower()) or re.search(rf"\b{re.escape(kw)}\b", title.lower()):
                        proj_tech.append(kw.title() if kw != "sql" else "SQL")
                        
                projects.append({
                    "title": title,
                    "description": desc,
                    "technologies": proj_tech
                })
                
    profile["projects"] = projects
    return profile


def parse_resume(file_path_or_stream, file_extension: str = None) -> CandidateParsedProfile:
    """Ingests a resume, extracts raw text, calls LLM or fallback heuristics, and returns Pydantic validation."""
    raw_text = extract_text(file_path_or_stream, file_extension)
    
    llm = _get_llm()
    if llm is None:
        # Fallback offline mode
        parsed_data = parse_locally(raw_text)
    else:
        # AI Mode
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            template = f.read()
            
        prompt = template.format(resume_text=raw_text)
        response = llm.invoke([HumanMessage(content=prompt)])
        parsed_data = _safe_loads(response.content)
        
    # Ensure correct types and return validated model
    parsed_data["raw_resume_text"] = raw_text
    return CandidateParsedProfile.model_validate(parsed_data)

