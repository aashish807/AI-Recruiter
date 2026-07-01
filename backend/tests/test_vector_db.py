import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.resume import CandidateParsedProfile, ExperienceSchema, ProjectSchema
from embeddings.generator import EmbeddingGenerator
from vector_db.store import add_candidate_vectors, search_aspect_vectors, reset_vector_database

def run_vector_db_test():
    print(">>> Phase 6 Vector Database verification initiated...")
    
    # 1. Reset DB
    reset_vector_database()
    
    # 2. Setup profiles for two mock candidates
    c1 = CandidateParsedProfile(
        name="Sarah Jenkins",
        skills=["Python", "FastAPI", "AWS", "Docker", "Kubernetes"],
        years_of_experience=8.0,
        raw_resume_text="Senior AWS engineer, FastAPI python microservices developer."
    )
    c2 = CandidateParsedProfile(
        name="Ankit Verma",
        skills=["Java", "Spring Boot", "Oracle"],
        years_of_experience=10.0,
        raw_resume_text="Legacy java developer, spring boot, oracle database on-premises."
    )

    generator = EmbeddingGenerator()
    
    # 3. Insert candidate vectors into FAISS aspect stores
    print("Generating and saving candidate vectors...")
    c1_vectors = generator.get_candidate_aspect_embeddings(c1)
    c2_vectors = generator.get_candidate_aspect_embeddings(c2)
    
    add_candidate_vectors("sarah_id", c1_vectors)
    add_candidate_vectors("ankit_id", c2_vectors)
    print("Vectors indexed inside FAISS aspect stores.")

    # 4. Search verification
    print("\nQuerying FAISS skills index for 'AWS FastAPI Kubernetes' requirements...")
    query_vector = generator.embed_text("AWS FastAPI Kubernetes container orchestration Python developer")
    
    results = search_aspect_vectors("skills", query_vector, k=5)
    print(f"Retrieval results: {results}")
    
    # Asserts check
    print("\nEvaluating retrieval asserts...")
    assert len(results) == 2
    
    # Sarah should rank higher than Ankit for AWS/FastAPI query
    top_cand, top_score = results[0]
    last_cand, last_score = results[1]
    
    assert top_cand == "sarah_id"
    assert top_score > last_score
    print(f"Assert match correct: Top rank is {top_cand} (Score: {top_score}%), runner-up is {last_cand} (Score: {last_score}%)")
    
    # 5. Clean up
    print("\nCleaning up local index files...")
    reset_vector_database()
    print(">>> Vector Database: ALL ASSERTS PASSED! FAISS indexing and retrieval are fully functional.")

if __name__ == "__main__":
    run_vector_db_test()
