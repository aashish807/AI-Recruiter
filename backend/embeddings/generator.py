import os
import json
from typing import List, Dict, Any

from models.resume import CandidateParsedProfile

class EmbeddingGenerator:
    def __init__(self, model_name: str = "text-embedding-3-large", local_model_name: str = "all-MiniLM-L6-v2"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.local_model_name = local_model_name
        self.openai_client = None
        self.local_client = None
        
        if self.api_key:
            # We configure OpenAI text-embedding-3-large
            try:
                from langchain_openai import OpenAIEmbeddings
                self.openai_client = OpenAIEmbeddings(model=self.model_name)
            except Exception as e:
                print(f"Warning: Failed to load OpenAIEmbeddings: {e}")
                self.api_key = None
                
        if not self.api_key:
            try:
                from sentence_transformers import SentenceTransformer
                self.local_client = SentenceTransformer(self.local_model_name)
            except Exception as e:
                print(f"Warning: Failed to load local SentenceTransformer: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a vector list of floats."""
        if not text or not text.strip():
            # Return dummy representation for empty inputs
            dim = 1536 if self.api_key else 384
            return [0.0] * dim
            
        if self.api_key and self.openai_client:
            try:
                return self.openai_client.embed_query(text)
            except Exception as e:
                print(f"OpenAI embedding failed, falling back: {e}")
                
        if self.local_client:
            try:
                vector = self.local_client.encode(text)
                return vector.tolist()
            except Exception as e:
                print(f"SentenceTransformer embedding failed, falling back: {e}")
                
        # Hard fallback to dummy list of floats for portability
        dim = 1536 if self.api_key else 384
        return [0.1] * dim

    def get_candidate_aspect_embeddings(self, profile: CandidateParsedProfile) -> Dict[str, List[float]]:
        """Generates all 6 multi-aspect embeddings specified in Stage 5."""
        
        # 1. Resume text
        resume_text = profile.raw_resume_text or ""
        if not resume_text:
            resume_text = f"Candidate Profile: {profile.name or 'Anonymized'}. Skills: {', '.join(profile.skills)}"

        # 2. Experience text
        exp_texts = []
        for exp in profile.experience:
            role_desc = f"Worked at {exp.company or 'N/A'} as {exp.role or 'N/A'} from {exp.start_date or 'N/A'} to {exp.end_date or 'N/A'}. Details: {exp.description or 'N/A'}"
            exp_texts.append(role_desc)
        experience_text = "\n".join(exp_texts) if exp_texts else "No work experience details provided."

        # 3. Projects text
        proj_texts = []
        for proj in profile.projects:
            proj_desc = f"Project: {proj.title or 'N/A'}. Description: {proj.description or 'N/A'}. Technologies: {', '.join(proj.technologies)}"
            proj_texts.append(proj_desc)
        projects_text = "\n".join(proj_texts) if proj_texts else "No projects details provided."

        # 4. Skills text
        skills_text = f"Skills: {', '.join(profile.skills)}. Technologies: {', '.join(profile.technologies)}"

        # 5. Career text
        career_text = f"Career Progression: Total Experience {profile.years_of_experience or 0.0} years. Companies: {', '.join(profile.companies)}. Roles: {', '.join([e.role for e in profile.experience if e.role])}"

        # 6. Behavior text
        behavior_text = f"Behavior and Traits: Leadership: {', '.join(profile.leadership)}. Soft Skills: {', '.join(profile.soft_skills)}. Responsibilities: {', '.join(profile.responsibilities)}. Certifications: {', '.join(profile.certifications)}"

        return {
            "resume": self.embed_text(resume_text),
            "experience": self.embed_text(experience_text),
            "projects": self.embed_text(projects_text),
            "skills": self.embed_text(skills_text),
            "career": self.embed_text(career_text),
            "behavior": self.embed_text(behavior_text)
        }
