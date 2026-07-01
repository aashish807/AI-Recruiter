import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.resume import CandidateParsedProfile, ExperienceSchema, ProjectSchema
from embeddings.generator import EmbeddingGenerator

def run_embeddings_test():
    print(">>> Phase 5 Embedding Generation verification initiated...")
    
    # 1. Setup mock parsed profile
    mock_profile = CandidateParsedProfile(
        name="Sarah Jenkins",
        email="sarah.j@gmail.com",
        phone="555-019-2834",
        education=["B.S. Computer Science"],
        skills=["Python", "Go", "AWS", "Docker", "Kubernetes"],
        experience=[
            ExperienceSchema(
                company="Techflow Inc",
                role="Lead Engineer",
                start_date="2021",
                end_date="Present",
                description="Architected AWS systems and Docker clusters."
            )
        ],
        companies=["Techflow Inc"],
        projects=[
            ProjectSchema(
                title="CloudDeploy",
                description="Helm packaging tool.",
                technologies=["Go", "Docker"]
            )
        ],
        technologies=["Python", "Go", "Docker", "AWS"],
        soft_skills=["Communication", "Collaboration"],
        leadership=["Guided team of 3 developers"],
        responsibilities=["CI/CD workflows", "Automated testing"],
        years_of_experience=8.0,
        raw_resume_text="Sarah Jenkins\nEmail: sarah.j@gmail.com\nLead Backend Engineer with 8 years experience building scalable AWS microservices."
    )


    # 2. Init generator
    print("Initializing Embedding Generator...")
    generator = EmbeddingGenerator()
    
    # 3. Generate aspect vectors
    print("Generating aspect embeddings for Candidate...")
    aspects = generator.get_candidate_aspect_embeddings(mock_profile)
    
    # 4. Asserts check
    print("\nEvaluating vector dimensions and non-null constraints...")
    required_aspects = ["resume", "experience", "projects", "skills", "career", "behavior"]
    
    for aspect in required_aspects:
        assert aspect in aspects
        vector = aspects[aspect]
        assert isinstance(vector, list)
        assert len(vector) > 0
        assert all(isinstance(x, float) for x in vector)
        print(f"Aspect '{aspect}' vector: {len(vector)} dimensions, parsed successfully.")

    print(">>> Embedding Generation: ALL ASSERTS PASSED! Multi-aspect embedding pipeline is fully functional.")

if __name__ == "__main__":
    run_embeddings_test()
