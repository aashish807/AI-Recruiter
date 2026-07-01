import os
import pandas as pd
from typing import List

# Directory to save export files
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "saved")

def export_candidate_list(ranked_candidates: List[dict], export_format: str = "csv") -> str:
    """Stage 12: Translates ranked candidate structures to CSV or Excel sheet and writes file to disk."""
    records = []
    
    # 1. Flatten nested candidate scores and AI evaluations
    for item in ranked_candidates:
        breakdown = item.get("aspect_breakdown", {})
        evaluation = item.get("evaluation", {})
        
        flat_record = {
            "Rank": item.get("rank"),
            "Name": item.get("name"),
            "Email": item.get("email"),
            "Match Score": item.get("score"),
            "Score Band": item.get("score_band"),
            "Semantic Match %": breakdown.get("semantic_score"),
            "Skills Match %": breakdown.get("skills_score"),
            "Experience Match %": breakdown.get("experience_score"),
            "Projects Match %": breakdown.get("projects_score"),
            "Behavior Score %": breakdown.get("behavior_score"),
            "Matched Skills": ", ".join(evaluation.get("matched_skills", [])),
            "Missing Skills": ", ".join(evaluation.get("missing_skills", []))
        }
        records.append(flat_record)
        
    # 2. Build Pandas DataFrame
    df = pd.DataFrame(records)
    
    # 3. Create target directory
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    # 4. Save to target format
    export_format = export_format.strip().lower()
    if export_format == "xlsx":
        filename = "candidate_rankings.xlsx"
        filepath = os.path.join(EXPORTS_DIR, filename)
        df.to_excel(filepath, index=False, engine="openpyxl")
    else:
        filename = "candidate_rankings.csv"
        filepath = os.path.join(EXPORTS_DIR, filename)
        df.to_csv(filepath, index=False)
        
    return filepath
