from pydantic import BaseModel
from typing import List, Optional, TypedDict

# --- API Models ---
class JobDescriptionRequest(BaseModel):
    jd_text: str

class ResumeUploadRequest(BaseModel):
    resume_text: str  # In the hackathon, extract text from PDF on frontend or simple endpoint

# --- LangGraph State Schema ---
class RecruiterState(TypedDict):
    jd_text: str
    resume_text: str
    
    # Populated by Agent 1 (Requirement Analyst)
    jd_requirements: Optional[dict]
    
    # Populated by Agent 2 & 3 (Resume & Behavior Analyst)
    candidate_profile: Optional[dict]
    
    # Populated by Agent 4 (Matchmaker)
    semantic_score: Optional[float]
    
    # Populated by Agent 5 (Explainability Agent)
    strengths: Optional[List[str]]
    risks: Optional[List[str]]
    final_recommendation: Optional[str]