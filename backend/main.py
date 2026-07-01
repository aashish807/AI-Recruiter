import os
import json
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Database setup imports
from database import Base, engine, get_db
from database import Candidate as DbCandidate
from database import Skill as DbSkill
from database import Project as DbProject
from database import Experience as DbExperience
from database import Job as DbJob
from database import Ranking as DbRanking
from database import Embedding as DbEmbedding

# Logic modules
from models.resume import CandidateParsedProfile
from models.job import JobParsedProfile
from utils.parser import extract_text
from utils.resume_parser import parse_resume
from utils.job_parser import parse_job
from embeddings.generator import EmbeddingGenerator
from vector_db.store import add_candidate_vectors, search_aspect_vectors
from retrieval.retriever import search_candidates
from ranking.engine import HybridRankingEngine


# Legacy schemas and agent workflow (to keep dashboard retro-compatible)
from schemas import JobDescriptionRequest, ResumeUploadRequest, RecruiterState
from agents import recruiter_agent_app
from vector_store import index_job_description

# Auto-initialize database schemas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RecruiterGPT API",
    description="Production-grade AI recruitment pipeline with modular agents, normalized schemas, and semantic search.",
    version="1.0.0"
)

# CORS setup for local React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for hackathon dashboard compatibility
current_jd_text = ""
_generator_instance = None

def _get_generator() -> EmbeddingGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = EmbeddingGenerator()
    return _generator_instance


# ==========================================
# RETRO-COMPATIBILITY ROUTE (Existing Dashboard)
# ==========================================

@app.post("/upload-jd")
async def upload_jd(req: JobDescriptionRequest, db: Session = Depends(get_db)):
    global current_jd_text
    current_jd_text = req.jd_text
    
    # 1. FAISS index raw string (legacy fallback)
    index_job_description("current_jd", req.jd_text)
    
    # 2. Sync to Database under persistent Job record
    try:
        job_parsed = parse_job(req.jd_text)
        db_job = DbJob(
            title=job_parsed.domain or "Job Requirement Ingested",
            description=req.jd_text
        )
        db.add(db_job)
        db.commit()
    except Exception as e:
        print(f"Warning: Failed to save job details to SQL: {e}")
        db.rollback()
        
    return {"message": "JD successfully ingested and embedded."}


@app.post("/rank")
async def rank_candidate(req: ResumeUploadRequest):
    global current_jd_text
    if not current_jd_text:
        raise HTTPException(status_code=400, detail="Please upload a JD first.")
    
    # Execute the LangGraph workflow exactly like before
    try:
        initial_state = {
            "jd_text": current_jd_text,
            "resume_text": req.resume_text,
            "jd_requirements": None,
            "candidate_profile": None,
            "semantic_score": None,
            "strengths": None,
            "risks": None,
            "final_recommendation": None
        }
        
        final_state = recruiter_agent_app.invoke(initial_state)

        jd_requirements = final_state.get("jd_requirements") or {}
        candidate_profile = final_state.get("candidate_profile") or {}
        jd_skills = jd_requirements.get("skills", []) if isinstance(jd_requirements, dict) else []
        candidate_skills = candidate_profile.get("tech_stack", []) if isinstance(candidate_profile, dict) else []
        candidate_skill_lookup = {item.lower(): item for item in candidate_skills}
        overlap = sorted({skill.lower() for skill in jd_skills if skill.lower() in candidate_skill_lookup})

        experience_years = candidate_profile.get("experience_years") if isinstance(candidate_profile, dict) else None
        project_count = len(candidate_profile.get("projects", [])) if isinstance(candidate_profile, dict) else 0
        jd_skill_count = len(jd_skills)
        overlap_count = len(overlap)
        overlap_ratio = round((overlap_count / jd_skill_count) if jd_skill_count else 0.0, 2)

        structured_score = round(min(
            100.0,
            (overlap_ratio * 40.0)
            + (min(float(experience_years or 0), 10.0) / 10.0 * 25.0)
            + (min(project_count, 5) / 5.0 * 10.0)
        ), 2)

        semantic_score = final_state.get("semantic_score")
        score_value = float(semantic_score) if semantic_score is not None else 0.0
        score_band = "strong" if score_value >= 75 else "moderate" if score_value >= 55 else "needs review"
        
        return {
            "score": score_value,
            "score_band": score_band,
            "strengths": final_state.get("strengths") or [],
            "risks": final_state.get("risks") or [],
            "recommendation": final_state.get("final_recommendation") or "",
            "bias_free_profile": candidate_profile,
            "jd_requirements": jd_requirements,
            "match_breakdown": {
                "jd_skills": jd_skills,
                "candidate_skills": candidate_skills,
                "overlap": overlap,
                "experience_years": experience_years,
                "project_count": project_count,
            },
            "match_factors": {
                "matched_tokens": overlap,
                "jd_skill_count": jd_skill_count,
                "candidate_skill_count": len(candidate_skills),
                "skill_overlap_count": overlap_count,
                "skill_overlap_ratio": overlap_ratio,
                "structured_score": structured_score,
                "experience_years": experience_years,
                "project_count": project_count,
                "contribution_weights": {
                    "skill_overlap": 40,
                    "experience": 25,
                    "projects": 10,
                },
            },
            "summary": {
                "jd_focus": jd_requirements.get("culture") if isinstance(jd_requirements, dict) else None,
                "candidate_focus": candidate_profile.get("career_growth_flags") if isinstance(candidate_profile, dict) else None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# NEW STAGE 18 API ENDPOINTS
# ==========================================

@app.post("/upload_resume", response_model=CandidateParsedProfile)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Stage 18: Upload and ingest raw candidate file, parse details, commit SQL, and index FAISS vectors."""
    # 1. Parse text from upload stream
    filename = file.filename
    _, ext = os.path.splitext(filename)
    try:
        contents = await file.read()
        file_stream = io.BytesIO(contents) if ext.lower() in (".pdf", ".docx") else io.StringIO(contents.decode("utf-8", errors="ignore"))
        
        # Parse profile using our parser engine (Phase 3)
        profile = parse_resume(file_stream, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest resume document: {e}")
        
    # 2. Write to PostgreSQL candidate schema tables (Phase 2)
    db_candidate = DbCandidate(
        name=profile.name or filename,
        email=profile.email,
        phone=profile.phone,
        experience_years=profile.years_of_experience,
        education=", ".join(profile.education) if profile.education else None,
        raw_resume_text=profile.raw_resume_text
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    
    # Write nested children skills
    for s in profile.skills:
        db_skill = DbSkill(candidate_id=db_candidate.id, skill_name=s)
        db.add(db_skill)
        
    # Write experience
    for exp in profile.experience:
        db_exp = DbExperience(
            candidate_id=db_candidate.id,
            company=exp.company,
            role=exp.role,
            start_date=exp.start_date,
            end_date=exp.end_date,
            description=exp.description
        )
        db.add(db_exp)
        
    # Write projects
    for proj in profile.projects:
        db_proj = DbProject(
            candidate_id=db_candidate.id,
            title=proj.title,
            description=proj.description,
            technologies=", ".join(proj.technologies) if proj.technologies else None
        )
        db.add(db_proj)
        
    db.commit()
    
    # 3. Generate aspect embeddings (Phase 5) and insert into FAISS Vector Database (Phase 6)
    try:
        generator = _get_generator()
        aspect_vectors = generator.get_candidate_aspect_embeddings(profile)
        
        # Save aspect mappings to FAISS indices
        add_candidate_vectors(db_candidate.id, aspect_vectors)
        
        # Save serialized representation to SQL Embedding table as well
        for aspect_name, float_list in aspect_vectors.items():
            db_emb = DbEmbedding(
                candidate_id=db_candidate.id,
                vector_type=aspect_name,
                embedding_vector=json.dumps(float_list)
            )
            db.add(db_emb)
        db.commit()
    except Exception as e:
        print(f"Warning: Failed to index embeddings in FAISS: {e}")
        
    profile.id = db_candidate.id
    return profile



@app.post("/upload_job", response_model=JobParsedProfile)
async def upload_job(req: JobDescriptionRequest, db: Session = Depends(get_db)):
    """Stage 18: Ingest raw Job Description text, parse it with GPT-4, and save to SQL."""
    global current_jd_text
    current_jd_text = req.jd_text
    
    # Parse Job requirements using parser engine (Phase 4)
    try:
        job_parsed = parse_job(req.jd_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Job Description: {e}")
        
    # Commit Job record to database
    db_job = DbJob(
        title=job_parsed.domain or "Ingested Job Description",
        description=req.jd_text
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Generate and save Job Embeddings to relational SQL database for metadata lookup
    try:
        generator = _get_generator()
        jd_vector = generator.embed_text(req.jd_text)
        db_emb = DbEmbedding(
            job_id=db_job.id,
            vector_type="jd_text",
            embedding_vector=json.dumps(jd_vector)
        )
        db.add(db_emb)
        db.commit()
    except Exception as e:
        print(f"Warning: Failed to save Job Embeddings: {e}")
        
    # Expose JobParsedProfile
    return job_parsed


@app.get("/candidates")
async def get_candidates(db: Session = Depends(get_db)):
    """Stage 18: Retrieve all candidates saved in the relational database."""
    candidates = db.query(DbCandidate).all()
    output = []
    for c in candidates:
        output.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "experience_years": c.experience_years,
            "education": c.education,
            "skills": [s.skill_name for s in c.skills],
            "experience": [{"company": e.company, "role": e.role} for e in c.experiences],
            "projects": [{"title": p.title, "technologies": p.technologies} for p in c.projects]
        })
    return output


@app.get("/rank")
async def get_rank(job_id: Optional[str] = None, query_text: Optional[str] = None, db: Session = Depends(get_db)):
    """Stage 18: Evaluate all candidates in FAISS vector database matching Job description query."""
    global current_jd_text
    
    # Resolve JD text
    search_query = query_text
    if not search_query and job_id:
        job_record = db.query(DbJob).filter(DbJob.id == job_id).first()
        if job_record:
            search_query = job_record.description
            
    if not search_query:
        # Fallback to current global description
        search_query = current_jd_text
        
    if not search_query:
        raise HTTPException(status_code=400, detail="Please upload a Job Description first or specify a query parameter.")
        
    # Execute Hybrid Ranker Blending Logic (Phase 8 / Stages 7-10)
    engine = HybridRankingEngine()
    candidates = db.query(DbCandidate).all()
    hybrid_results = engine.get_candidate_hybrid_scores(search_query, candidates, db)
    
    ranked_list = []
    seen_names = set()
    for item in hybrid_results:
        name_key = item["name"].strip().lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        
        score = item["score"]
        score_band = "strong" if score >= 75 else "moderate" if score >= 55 else "needs review"
        
        # Build detailed match breakdown details for React cockpit UI
        eval_data = item["evaluation"]
        aspect_bk = item["aspect_breakdown"].copy()
        aspect_bk.update({
            "experience_years": item["experience_years"],
            "project_count": item["project_count"],
            "jd_skills": eval_data.get("matched_skills", []) + eval_data.get("missing_skills", []),
            "candidate_skills": item["candidate_skills"],
            "overlap": eval_data.get("matched_skills", [])
        })
        
        ranked_list.append({
            "rank": len(ranked_list) + 1,
            "id": item["candidate_id"],
            "name": item["name"],
            "score": score,
            "score_band": score_band,
            "email": item["email"],
            "aspect_breakdown": aspect_bk,
            "evaluation": item["evaluation"]
        })

        
    return ranked_list



from fastapi.responses import FileResponse
from reports.generator import generate_recruiter_report

@app.get("/candidates/{candidate_id}/report")
async def get_candidate_report(candidate_id: str, query_text: Optional[str] = None, db: Session = Depends(get_db)):
    """Stage 11: Generate and download the Recruiter Intelligence Report for a candidate."""
    global current_jd_text
    search_query = query_text or current_jd_text or "General Technical Position"
    
    try:
        report_path = generate_recruiter_report(candidate_id, search_query, db)
        if not os.path.exists(report_path):
            raise HTTPException(status_code=500, detail="Report file was not created.")
            
        return FileResponse(
            path=report_path,
            filename=os.path.basename(report_path),
            media_type="text/markdown"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
from reports.generator import generate_recruiter_report
from exports.exporter import export_candidate_list

@app.get("/candidates/export")
async def get_candidates_export(format: str = "csv", query_text: Optional[str] = None, db: Session = Depends(get_db)):
    """Stage 12: Ingest candidates, rank them, compile CSV/Excel structures and download the export file."""
    global current_jd_text
    search_query = query_text or current_jd_text or "General Technical Position"
    
    # 1. Fetch and rank candidates using HybridRankingEngine
    engine = HybridRankingEngine()
    candidates = db.query(DbCandidate).all()
    hybrid_results = engine.get_candidate_hybrid_scores(search_query, candidates, db)
    
    # 2. Form structured ranked list
    ranked_list = []
    seen_names = set()
    for item in hybrid_results:
        name_key = item["name"].strip().lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        
        ranked_list.append({
            "rank": len(ranked_list) + 1,
            "name": item["name"],
            "email": item["email"],
            "score": item["score"],
            "score_band": "strong" if item["score"] >= 75 else "moderate" if item["score"] >= 55 else "needs review",
            "aspect_breakdown": item["aspect_breakdown"],
            "evaluation": item["evaluation"]
        })

        
    # 3. Export structure to target file on disk
    try:
        export_path = export_candidate_list(ranked_list, format)
        if not os.path.exists(export_path):
            raise HTTPException(status_code=500, detail="Export file creation failed.")
            
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format.lower() == "xlsx" else "text/csv"
        
        return FileResponse(
            path=export_path,
            filename=os.path.basename(export_path),
            media_type=media_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Import io library inside module context defensively
import io