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

def run_semantic_search_test():
    print(">>> Phase 7 Semantic Search Integration verification initiated...")
    
    # 1. Reset databases
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
    
    # 2. Test JD Ingestion Endpoint
    print("\nTesting POST /upload_job...")
    jd_payload = {
        "jd_text": "Senior Cloud Backend Developer. We need Python, Go, AWS, Docker, and Kubernetes microservices experience."
    }
    response_jd = client.post("/upload_job", json=jd_payload)
    assert response_jd.status_code == 200
    jd_data = response_jd.json()
    print("Parsed Job JSON:")
    print(json.dumps(jd_data, indent=2))
    assert "experience_level" in jd_data
    
    # 3. Test Resume Ingestion Endpoint
    print("\nTesting POST /upload_resume...")
    mock_resume_path = os.path.join(os.path.dirname(__file__), "resumes", "mock_resume.txt")
    if not os.path.exists(mock_resume_path):
        print(f"Error: Mock resume not found at {mock_resume_path}")
        sys.exit(1)
        
    with open(mock_resume_path, "rb") as f:
        response_resume = client.post(
            "/upload_resume",
            files={"file": ("mock_resume.txt", f, "text/plain")}
        )
        
    assert response_resume.status_code == 200
    resume_data = response_resume.json()
    print("Parsed Resume JSON:")
    print(json.dumps(resume_data, indent=2))
    assert resume_data["name"] == "Sarah Jenkins"
    assert "Python" in resume_data["skills"]
    
    # 4. Check Database persistence
    print("\nChecking PostgreSQL/SQLite relational state...")
    db = SessionLocal()
    candidates = db.query(Candidate).all()
    assert len(candidates) == 1
    assert candidates[0].name == "Sarah Jenkins"
    print(f"Database Candidate: {candidates[0].name} successfully verified.")
    db.close()
    
    # 5. Test GET /candidates
    print("\nTesting GET /candidates...")
    response_list = client.get("/candidates")
    assert response_list.status_code == 200
    candidates_list = response_list.json()
    assert len(candidates_list) == 1
    print(f"Candidates list returned: {candidates_list}")
    
    # 6. Test GET /rank (Semantic Search)
    print("\nTesting GET /rank...")
    response_rank = client.get("/rank")
    assert response_rank.status_code == 200
    rankings = response_rank.json()
    print("Ranked Results list:")
    print(json.dumps(rankings, indent=2))
    
    assert len(rankings) == 1
    assert rankings[0]["name"] == "Sarah Jenkins"
    assert rankings[0]["score"] > 50.0
    
    # 7. Clean up
    reset_vector_database()
    print("\n>>> Semantic Search Integration: ALL ENDPOINTS VERIFIED & ASSERTS PASSED!")

if __name__ == "__main__":
    run_semantic_search_test()
