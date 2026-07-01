import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.job_parser import parse_job

def run_job_parser_test():
    print(">>> Phase 4 JD Understanding verification initiated...")
    
    mock_jd_path = os.path.join(os.path.dirname(__file__), "jobs", "mock_jd.txt")
    if not os.path.exists(mock_jd_path):
        print(f"Error: Mock JD not found at {mock_jd_path}")
        sys.exit(1)
        
    print(f"Parsing mock Job Description at: {mock_jd_path}")
    with open(mock_jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
        
    profile = parse_job(jd_text)
    
    # Dump result for debugging
    print("\nParsed Result JSON Output:")
    print(profile.model_dump_json(indent=2))
    
    # Assert check
    print("\nEvaluating asserts...")
    assert profile.experience_level in ("Senior", "Lead")
    
    # Check that core technologies are in the tech stack or must have skills
    all_extracted_skills = [s.lower() for s in (profile.must_have_skills + profile.technology_stack)]
    expected_skills = ["python", "fastapi", "aws", "docker", "kubernetes", "go"]
    
    # Assert that at least most expected skills were found
    matches = [s for s in expected_skills if s in all_extracted_skills]
    print(f"Matched skills: {matches}")
    assert len(matches) >= 4
    
    print(">>> JD Understanding: ALL ASSERTS PASSED! Job Parsing engine is fully functional.")

if __name__ == "__main__":
    run_job_parser_test()
