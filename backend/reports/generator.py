import os
from sqlalchemy.orm import Session
from database import Candidate as DbCandidate
from ranking.engine import HybridRankingEngine

# Directory to save report assets
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "saved")

def generate_recruiter_report(candidate_id: str, search_query: str, db: Session) -> str:
    """Stage 11: Compiles scoring metrics and AI evaluations, formats a Markdown report, and saves it to disk."""
    # 1. Fetch Candidate details
    c = db.query(DbCandidate).filter(DbCandidate.id == candidate_id).first()
    if not c:
        raise ValueError(f"Candidate not found with ID {candidate_id}")
        
    # 2. Run Hybrid Score calculations
    engine = HybridRankingEngine()
    hybrid_list = engine.get_candidate_hybrid_scores(search_query, [c], db)
    if not hybrid_list:
        raise ValueError("Failed to calculate candidate hybrid scores.")
        
    res = hybrid_list[0]
    score = res["score"]
    score_band = "Strong Fit" if score >= 75 else "Moderate Fit" if score >= 55 else "Needs Review"
    breakdown = res["aspect_breakdown"]
    eval_dict = res["evaluation"]

    # 3. Format beautiful Markdown
    report_md = f"""# RECRUITMENT INTELLIGENCE PLATFORM
## CANDIDATE EVALUATION REPORT: {res["name"].upper()}

---
### EXECUTIVE SUMMARY
* **Candidate Name:** {res["name"]}
* **Contact Email:** {res["email"] or "N/A"}
* **Experience Level:** {c.experience_years or 0.0} years
* **Target Role Context:** Ingested Job Description
* **Match Evaluation:** **{score_band} ({score} / 100)**

---
### COMPOSITE SCORE BREAKDOWN (HYBRID ENGINE)
* **Core Semantic Match (40%):** {breakdown["semantic_score"]}%
* **Technical Skills Coverage (20%):** {breakdown["skills_score"]}%
* **Work Experience Context (15%):** {breakdown["experience_score"]}%
* **System Projects Portfolio (10%):** {breakdown["projects_score"]}%
* **Career Growth Indicators (5%):** {breakdown["career_score"]}%
* **Education Credentials (5%):** {breakdown["education_score"]}%
* **Behavioral Intelligence (5%):** {breakdown["behavior_score"]}%

---
### STRENGTHS & CORE CAPABILITIES
{chr(10).join([f"* {s}" for s in eval_dict.get("strengths", [])])}

### IMPROVEMENT AREAS & TECHNICAL GAPS
{chr(10).join([f"* {w}" for w in eval_dict.get("weaknesses", [])])}

---
### DETAILED AGENT FIT LOGS
* **Why Selected:** {eval_dict.get("why_selected", "N/A")}
* **Transferable Skills:** {', '.join(eval_dict.get("transferable_skills", []))}
* **Leadership Qualities:** {', '.join(eval_dict.get("leadership", []))}
* **Technical Depth Analysis:** {', '.join(eval_dict.get("technical_depth", []))}
* **Culture Fit Alignment:** {', '.join(eval_dict.get("culture_fit", []))}
* **Education Assessment:** {c.education or "N/A"}

---
### BEHAVIORAL INTELLIGENCE INSIGHTS (STAGE 9)
* **Behavior Confidence Score:** {eval_dict.get("behavior_score", 70)}%
{chr(10).join([f"* {bi}" for bi in eval_dict.get("behavioral_insights", [])])}

---
### RECRUITER VERDICT & EXPLANATION
{eval_dict.get("recruiter_explanation", "No additional notes.")}

---
*Report generated automatically by RecruiterGPT Intelligence Engine. Confidential - For Internal Recruiter Use Only.*
"""

    # 4. Save report file to disk
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_filename = f"report_{candidate_id}_{res['name'].replace(' ', '_').lower()}.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    return report_path
