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

def run_exports_test():
    print(">>> Phase 10 Candidate Exports verification initiated...")
    
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
    
    # 2. Ingest Job
    client.post("/upload_job", json={"jd_text": "Required: Python developer."})
    
    # 3. Ingest candidate resume
    mock_resume_path = os.path.join(os.path.dirname(__file__), "resumes", "mock_resume.txt")
    client.post(
        "/upload_resume",
        files={"file": ("mock_resume.txt", open(mock_resume_path, "rb"), "text/plain")}
    )
    
    # 4. Test CSV Export
    print("Requesting CSV candidate exports...")
    csv_response = client.get("/candidates/export?format=csv")
    assert csv_response.status_code == 200
    csv_data = csv_response.text
    print("\nCSV Head Rows Output:")
    print(csv_data[:300])
    
    assert "Rank,Name,Email,Match Score,Score Band" in csv_data
    assert "Sarah Jenkins" in csv_data

    # 5. Test Excel Export
    print("\nRequesting Excel candidate exports...")
    xlsx_response = client.get("/candidates/export?format=xlsx")
    assert xlsx_response.status_code == 200
    assert len(xlsx_response.content) > 1000 # Excel file binary size check
    
    # 6. Verify local persistent file caches
    saved_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports", "saved")
    files = os.listdir(saved_dir)
    print(f"\nPersisted export structures on disk cache: {files}")
    assert "candidate_rankings.csv" in files
    assert "candidate_rankings.xlsx" in files

    # Clean up
    reset_vector_database()
    print("\n>>> Candidate Exports: ALL ASSERTS PASSED! CSV and Excel exporter sheets are fully functional.")

if __name__ == "__main__":
    run_exports_test()
