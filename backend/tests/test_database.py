import sys
import os
import json

# Add parent directory to sys.path so we can import from database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base, SessionLocal, engine
from database import Candidate, Job, Skill, Project, Experience, Ranking, Embedding

def run_db_test():
    print(">>> Phase 2 Database verification initiated...")
    
    # 1. Initialize Tables (Create recruiter.db if sqlite)
    print("Step 1: Creating database schemas...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

    # 2. Open Session
    db = SessionLocal()
    try:
        # 3. Create a Job Description record
        print("Step 2: Inserting a mock Job Description...")
        job = Job(
            title="Senior Cloud Architect",
            description="Looking for an AWS developer expert in container systems and FastAPI backend integrations."
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        print(f"Job inserted: {job.title} (ID: {job.id})")

        # 4. Create a Candidate record
        print("Step 3: Inserting a mock Candidate profile...")
        candidate = Candidate(
            name="Alice Vance",
            email="alice@cloudcorp.com",
            phone="123-456-7890",
            experience_years=7.5,
            education="Master of Science in Computing",
            raw_resume_text="Senior engineer with 7+ years building AWS cloud products. Experienced with Python, Docker, Go."
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        print(f"Candidate inserted: {candidate.name} (ID: {candidate.id})")

        # 5. Add Skill, Project, Experience related to Candidate
        print("Step 4: Inserting nested child relationships...")
        skill1 = Skill(candidate_id=candidate.id, skill_name="AWS")
        skill2 = Skill(candidate_id=candidate.id, skill_name="Docker")
        project = Project(candidate_id=candidate.id, title="Microservices Pipeline", description="CI/CD deployment for FastAPI apps.", technologies="Python, Docker, GitHub Actions")
        experience = Experience(candidate_id=candidate.id, company="CloudCorp Inc", role="Lead Engineer", start_date="2020", end_date="Present", description="Architected AWS systems.")
        
        db.add_all([skill1, skill2, project, experience])
        db.commit()
        print("Child relationships inserted successfully.")

        # 6. Add Ranking
        print("Step 5: Inserting Candidate Evaluation Ranking report...")
        ranking = Ranking(
            job_id=job.id,
            candidate_id=candidate.id,
            score=94.5,
            score_band="strong",
            recommendation="Strong recommendation for phone interview screening.",
            strengths=json.dumps(["Solid AWS foundations", "Deep Docker knowledge"]),
            risks=json.dumps([])
        )
        db.add(ranking)
        
        # 7. Add Embedding
        print("Step 6: Inserting mock float embedding vector...")
        embedding = Embedding(
            candidate_id=candidate.id,
            vector_type="resume",
            embedding_vector=json.dumps([0.142, -0.992, 0.441, 0.009] * 384) # 1536 dim mock
        )
        db.add(embedding)
        db.commit()
        print("Ranking & Embedding saved.")

        # 8. Query and Verify
        print("\nStep 7: Executing verification query updates...")
        fetched_candidate = db.query(Candidate).filter(Candidate.id == candidate.id).first()
        assert fetched_candidate is not None
        assert len(fetched_candidate.skills) == 2
        assert fetched_candidate.projects[0].title == "Microservices Pipeline"
        assert fetched_candidate.experiences[0].company == "CloudCorp Inc"

        fetched_ranking = db.query(Ranking).filter(Ranking.job_id == job.id, Ranking.candidate_id == candidate.id).first()
        assert fetched_ranking is not None
        assert fetched_ranking.score == 94.5
        
        strengths = json.loads(fetched_ranking.strengths)
        assert "Solid AWS foundations" in strengths

        print(">>> Verification queries: ALL ASSERTS PASSED! Database schema is correct.")

    except Exception as e:
        print(f"Error during verification: {e}")
        db.rollback()
        raise e
    finally:
        # Clean up database test records so we start fresh next time
        print("Step 8: Cleaning up test data from session...")
        db.query(Embedding).delete()
        db.query(Ranking).delete()
        db.query(Skill).delete()
        db.query(Project).delete()
        db.query(Experience).delete()
        db.query(Candidate).delete()
        db.query(Job).delete()
        db.commit()
        db.close()
        print("Cleanup done.")

if __name__ == "__main__":
    run_db_test()
