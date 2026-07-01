import json
import os
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from models.job import JobParsedProfile

# Load the prompt template
PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "job_parsing.txt")

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

def parse_job_locally(text: str) -> Dict[str, Any]:
    """Heuristic fallback extraction when OpenAI key is missing."""
    profile = {
        "must_have_skills": [],
        "preferred_skills": [],
        "experience_level": "Mid",
        "responsibilities": [],
        "technology_stack": [],
        "industry": "Tech",
        "domain": "Software Engineering",
        "soft_skills": [],
        "leadership_expectations": [],
        "education": None,
        "nice_to_have_skills": [],
        "certifications": []
    }

    # Extract experience level
    text_lower = text.lower()
    if "senior" in text_lower:
        profile["experience_level"] = "Senior"
    elif "lead" in text_lower or "principal" in text_lower:
        profile["experience_level"] = "Lead"
    elif "junior" in text_lower:
        profile["experience_level"] = "Junior"
    elif "staff" in text_lower:
        profile["experience_level"] = "Staff"

    # Extract technology keywords
    keywords = ["python", "fastapi", "aws", "docker", "kubernetes", "java", "spring boot", "react", "javascript", "sql", "go", "devops"]
    found_tech = []
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            found_tech.append(kw.title() if kw != "sql" else "SQL")
    profile["technology_stack"] = found_tech
    profile["must_have_skills"] = found_tech[:3]
    profile["preferred_skills"] = found_tech[3:5]
    profile["nice_to_have_skills"] = found_tech[5:]

    # Soft skills
    soft_kws = ["communication", "collaborate", "teamwork", "ownership", "agile", "mentor"]
    for sk in soft_kws:
        if sk in text_lower:
            profile["soft_skills"].append(sk.title())

    # Education guesses
    if "degree" in text_lower or "bachelor" in text_lower:
        profile["education"] = "Bachelor's Degree in Computer Science or equivalent"
    elif "master" in text_lower:
        profile["education"] = "Master's Degree in Computer Science"

    return profile

def parse_job(jd_text: str) -> JobParsedProfile:
    """Parses a Job Description string, runs LLM/Heuristics parsing, and returns validated Pydantic profile."""
    if not jd_text.strip():
        raise ValueError("Job Description cannot be empty.")
        
    llm = _get_llm()
    if llm is None:
        # Fallback offline mode
        parsed_data = parse_job_locally(jd_text)
    else:
        # AI Mode
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            template = f.read()
            
        prompt = template.format(jd_text=jd_text)
        response = llm.invoke([HumanMessage(content=prompt)])
        parsed_data = _safe_loads(response.content)
        
    # Return validated model representation
    return JobParsedProfile.model_validate(parsed_data)
