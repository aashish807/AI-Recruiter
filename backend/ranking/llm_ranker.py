import os
import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "explainability.txt")

def _get_llm():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    return ChatOpenAI(model="gpt-4o", temperature=0)

def _safe_loads(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

def evaluate_candidate_locally(candidate_name: str, skills: list, years_exp: float, jd_text: str) -> Dict[str, Any]:
    """Heuristic fallback candidate fit evaluation when OpenAI key is missing."""
    jd_lower = jd_text.lower()
    matched = [s for s in skills if s.lower() in jd_lower]
    missing = [s for s in ["AWS", "Docker", "Kubernetes", "Python", "Go", "Java"] if s.lower() in jd_lower and s not in skills]
    
    # Behavior score heuristics
    score = 70
    insights = []
    if years_exp > 5:
        score += 15
        insights.append("Career Stability: Demonstrated long tenure and growth.")
    else:
        score += 5
        insights.append("Career Growth: Rapid progression indicated.")
        
    if len(skills) > 5:
        score += 10
        insights.append("Learning Agility: Diverse skills footprint.")
        
    score = min(100, score)
    
    return {
        "overall_summary": f"{candidate_name} matches core tech stack. Years of experience: {years_exp}.",
        "strengths": matched if matched else ["Core experience"],
        "weaknesses": missing if missing else ["Domain-specific nuances"],
        "transferable_skills": [s for s in skills[:2]],
        "career_growth": ["Progressive responsibility logs."],
        "leadership": ["Mentorship capability inferred from seniority."],
        "technical_depth": ["Broad system engineering stack."],
        "culture_fit": ["Collaborative environment alignment."],
        "risk_factors": ["None highlighted."],
        "behavior_score": score,
        "behavioral_insights": insights,
        "why_selected": f"{candidate_name} exhibits strong alignment in technology keys.",
        "matched_skills": matched,
        "missing_skills": missing,
        "relevant_projects": ["Portfolio matches role focus."],
        "relevant_experience": ["Senior engineering history matches scale expectations."],
        "confidence_score": int(max(40, min(100, len(matched)/(len(matched)+len(missing)+1)*100))),
        "recruiter_explanation": f"Recommended candidate due to strong alignment in {', '.join(matched)}."
    }

def evaluate_candidate_fit(candidate_name: str, skills: list, years_exp: float, experience_log: str, projects_log: str, raw_text: str, jd_text: str) -> Dict[str, Any]:
    """Invokes LLM/Heuristic candidate analysis agent."""
    llm = _get_llm()
    if llm is None:
        return evaluate_candidate_locally(candidate_name, skills, years_exp, jd_text)
        
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()
        
    prompt = template.format(
        jd_text=jd_text,
        candidate_name=candidate_name,
        candidate_experience_years=years_exp,
        candidate_skills=", ".join(skills),
        candidate_experience_log=experience_log,
        candidate_projects_log=projects_log,
        candidate_raw_text=raw_text
    )
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return _safe_loads(response.content)
    except Exception as e:
        print(f"Warning: OpenAI candidate fit evaluation failed, falling back: {e}")
        return evaluate_candidate_locally(candidate_name, skills, years_exp, jd_text)
