import os
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from embeddings.generator import EmbeddingGenerator
from vector_db.store import search_aspect_vectors
from ranking.llm_ranker import evaluate_candidate_fit

# Default Stage 8 Weights
DEFAULT_WEIGHTS = {
    "semantic": 0.40,
    "skills": 0.20,
    "experience": 0.15,
    "projects": 0.10,
    "career": 0.05,
    "education": 0.05,
    "behavior": 0.05
}

def compute_education_score(education_text: str) -> float:
    """Heuristic logic to score candidate educational backgrounds."""
    if not education_text:
        return 50.0
    text_lower = education_text.lower()
    if "phd" in text_lower or "doctor" in text_lower:
        return 100.0
    elif "master" in text_lower or "m.s." in text_lower or "m.tech" in text_lower:
        return 90.0
    elif "bachelor" in text_lower or "b.s." in text_lower or "b.tech" in text_lower:
        return 80.0
    return 70.0

class HybridRankingEngine:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = DEFAULT_WEIGHTS.copy()
        if weights:
            self.weights.update(weights)
        self.generator = EmbeddingGenerator()

    def get_candidate_hybrid_scores(self, jd_text: str, db_candidates: List[Any], db: Session) -> List[Dict[str, Any]]:
        """Orchestrates Stage 7-10 Hybrid scoring pipeline for a list of SQL candidate records."""
        if not db_candidates or not jd_text.strip():
            return []

        # 1. Generate query vectors for JD
        jd_embeddings = {
            "resume": self.generator.embed_text(jd_text),
            "skills": self.generator.embed_text(jd_text),
            "experience": self.generator.embed_text(jd_text),
            "projects": self.generator.embed_text(jd_text),
            "career": self.generator.embed_text(jd_text),
        }

        # 2. Retrieve FAISS match results for each aspect
        aspect_scores: Dict[str, Dict[str, float]] = {}
        for aspect in ["resume", "skills", "experience", "projects", "career"]:
            results = search_aspect_vectors(aspect, jd_embeddings[aspect], k=100)
            aspect_scores[aspect] = {cand_id: score for cand_id, score in results}

        ranked_candidates = []
        
        # 3. Process each candidate and compute hybrid scores
        for c in db_candidates:
            cand_id = c.id
            
            # Retrieve aspect scores from FAISS search mappings (default to 50 if missing)
            semantic_score = aspect_scores["resume"].get(cand_id, 50.0)
            skills_score = aspect_scores["skills"].get(cand_id, 50.0)
            experience_score = aspect_scores["experience"].get(cand_id, 50.0)
            projects_score = aspect_scores["projects"].get(cand_id, 50.0)
            career_score = aspect_scores["career"].get(cand_id, 50.0)
            
            # Compute education score
            education_score = compute_education_score(c.education)

            # 4. Invoke LLM Candidate Understanding & Behavior Evaluation (Stage 7 & 9)
            skills_list = [s.skill_name for s in c.skills]
            experience_log = "\n".join([f"{e.company} ({e.role}): {e.description}" for e in c.experiences])
            projects_log = "\n".join([f"{p.title}: {p.technologies}" for p in c.projects])
            
            evaluation = evaluate_candidate_fit(
                candidate_name=c.name,
                skills=skills_list,
                years_exp=c.experience_years or 0.0,
                experience_log=experience_log,
                projects_log=projects_log,
                raw_text=c.raw_resume_text or "",
                jd_text=jd_text
            )
            
            behavior_score = float(evaluation.get("behavior_score", 70.0))

            # 5. Blend weights (Stage 8)
            final_composite_score = (
                self.weights["semantic"] * semantic_score +
                self.weights["skills"] * skills_score +
                self.weights["experience"] * experience_score +
                self.weights["projects"] * projects_score +
                self.weights["career"] * career_score +
                self.weights["education"] * education_score +
                self.weights["behavior"] * behavior_score
            )
            final_composite_score = round(final_composite_score, 2)

            ranked_candidates.append({
                "candidate_id": cand_id,
                "name": c.name,
                "email": c.email,
                "score": final_composite_score,
                "experience_years": c.experience_years or 0.0,
                "project_count": len(c.projects),
                "candidate_skills": skills_list,
                "aspect_breakdown": {
                    "semantic_score": semantic_score,
                    "skills_score": skills_score,
                    "experience_score": experience_score,
                    "projects_score": projects_score,
                    "career_score": career_score,
                    "education_score": education_score,
                    "behavior_score": behavior_score,
                },
                "evaluation": evaluation
            })


        # Sort candidates descending by hybrid score
        return sorted(ranked_candidates, key=lambda x: x["score"], reverse=True)
