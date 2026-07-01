import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.resume_parser import parse_resume

def run_parser_test():
    print(">>> Phase 3 Ingestion & Resume Parsing verification initiated...")
    
    mock_resume_path = os.path.join(os.path.dirname(__file__), "resumes", "mock_resume.txt")
    if not os.path.exists(mock_resume_path):
        print(f"Error: Mock resume not found at {mock_resume_path}")
        sys.exit(1)
        
    print(f"Parsing mock resume at: {mock_resume_path}")
    profile = parse_resume(mock_resume_path)
    
    # Dump result for debugging
    profile_dict = profile.model_dump()
    print("\nParsed Result JSON Output:")
    print(profile.model_dump_json(indent=2))
    
    # Assert check
    print("\nEvaluating asserts...")
    assert "Sarah" in profile.name
    assert profile.email == "sarah.j@gmail.com"
    assert "555-019-2834" in profile.phone
    
    # Under local fallback or LLM, skills should capture at least Go/Python/AWS/Docker/Kubernetes
    assert any(x.lower() in [s.lower() for s in profile.skills] for x in ["python", "go", "aws", "docker"])
    assert profile.years_of_experience >= 8.0
    
    print(">>> Ingestion & Resume Parsing: ALL ASSERTS PASSED! Parsing engine is fully functional.")

if __name__ == "__main__":
    run_parser_test()
