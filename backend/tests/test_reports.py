import sys
import os
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, engine, SessionLocal
from database import Candidate, Job, Skill, Project, Experience, Ranking, Embedding
from vector_db.store import reset_vector_database

client = TestClient(app)

def run_reports_test():
    print(">>> Phase 9 Recruiter Reports verification initiated...")
    
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
    
    # 2. Ingest job description
    client.post("/upload_job", json={"jd_text": "Required: Python FastAPI Docker expert."})
    
    # 3. Ingest resume
    mock_resume_path = os.path.join(os.path.dirname(__file__), "resumes", "mock_resume.txt")
    client.post(
        "/upload_resume",
        files={"file": ("mock_resume.txt", open(mock_resume_path, "rb"), "text/plain")}
    )
    
    # 4. Get candidate list to retrieve the generated ID
    cands_response = client.get("/candidates")
    assert cands_response.status_code == 200
    cands = cands_response.json()
    assert len(cands) == 1
    candidate_id = cands[0]["id"]
    print(f"Retrieved candidate ID: {candidate_id}")
    
    # 5. Fetch report file
    print(f"Requesting report download for candidate ID: {candidate_id}...")
    report_response = client.get(f"/candidates/{candidate_id}/report")
    assert report_response.status_code == 200
    report_text = report_response.text
    
    # Verify contents
    print("\nVerified Report Content Snippet:")
    print(report_text[:400])
    
    assert "RECRUITMENT INTELLIGENCE PLATFORM" in report_text
    assert "Sarah Jenkins" in report_text
    assert "COMPOSITE SCORE BREAKDOWN" in report_text
    
    # 6. Verify file is persisted under backend/reports/saved/
    saved_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "saved")
    files = os.listdir(saved_dir)
    print(f"\nPersisted report files in disk cache: {files}")
    assert len(files) >= 1
    
    # Clean up
    reset_vector_database()
    print("\n>>> Recruiter Reports: ALL ASSERTS PASSED! Report compilation and download routes are fully functional.")

if __name__ == "__main__":
    run_reports_test()
