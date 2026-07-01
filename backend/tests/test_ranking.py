import sys
import os
import json
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, engine, SessionLocal
from database import Candidate, Job, Skill, Project, Experience, Ranking, Embedding
from vector_db.store import reset_vector_database

client = TestClient(app)

def run_ranking_test():
    print(">>> Phase 8 Hybrid Ranking & Explainability verification initiated...")
    
    # 1. Clear database
    reset_vector_database()
    db = SessionLocal()
    db.query(Embedding).delete()
    db.query(Ranking).delete()
    db.query(Skill).delete()
    db.query(Project).delete()
    db.query(Experience).delete()
    db.query(Candidate).delete()
    db.query(DbJob := Job).delete()
    db.commit()
    db.close()
    
    # 2. Upload Job
    print("Ingesting job description...")
    jd_payload = {"jd_text": "Senior Software Architect. Required: Python, FastAPI, Docker, Cloud Kubernetes architecture."}
    client.post("/upload_job", json=jd_payload)

    # 3. Upload Candidate
    print("Ingesting candidate resume file...")
    mock_resume_path = os.path.join(os.path.dirname(__file__), "resumes", "mock_resume.txt")
    with open(mock_resume_path, "rb") as f:
        client.post(
            "/upload_resume",
            files={"file": ("mock_resume.txt", f, "text/plain")}
        )

    # 4. Request ranked evaluation (GET /rank)
    print("\nRunning Hybrid score matches (GET /rank)...")
    response = client.get("/rank")
    assert response.status_code == 200
    results = response.json()
    
    # Dump formatted result
    print("\nRanked Output details:")
    print(json.dumps(results, indent=2))
    
    # 5. Evaluations & Asserts
    print("\nEvaluating hybrid factor assertions...")
    assert len(results) == 1
    item = results[0]
    assert item["name"] == "Sarah Jenkins"
    
    # Verify aspect breakdown exists
    breakdown = item["aspect_breakdown"]
    assert "semantic_score" in breakdown
    assert "skills_score" in breakdown
    assert "experience_score" in breakdown
    assert "projects_score" in breakdown
    assert "career_score" in breakdown
    assert "education_score" in breakdown
    assert "behavior_score" in breakdown
    
    # Verify AI explanation parameters exist
    evaluation = item["evaluation"]
    assert "overall_summary" in evaluation
    assert "strengths" in evaluation
    assert "weaknesses" in evaluation
    assert "why_selected" in evaluation
    assert "recruiter_explanation" in evaluation
    assert "behavior_score" in evaluation
    assert "behavioral_insights" in evaluation

    print("\n>>> Hybrid Ranking & Explainability Agent: ALL ASSERTS PASSED! Blending and reasoning pipeline is fully functional.")

if __name__ == "__main__":
    run_ranking_test()
