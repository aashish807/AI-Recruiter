import json
import csv
import sys
import os
import heapq
from datetime import datetime

# Key skills we want to see for this role
TARGET_SKILLS = {
    "python": 3.0,
    "sentence-transformers": 4.0,
    "faiss": 4.0,
    "pinecone": 4.0,
    "weaviate": 4.0,
    "qdrant": 4.0,
    "milvus": 4.0,
    "opensearch": 3.0,
    "elasticsearch": 2.0,
    "ndcg": 4.0,
    "mrr": 4.0,
    "map": 4.0,
    "rag": 3.0,
    "llm": 2.0,
    "machine learning": 1.0,
    "pytorch": 2.0,
    "deep learning": 1.0,
    "evaluation": 2.0,
    "retrieval": 4.0,
    "hybrid search": 4.0,
}

SERVICES_COMPANIES = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini", "mindtree", "hcl", "tech mahindra"]

def is_honeypot(cand):
    # 1. Total years of experience > 45 is extremely unlikely for this cohort
    yoe = cand.get("profile", {}).get("years_of_experience", 0)
    if yoe > 45: return True
    
    # 2. Check for impossible skill durations
    skills = cand.get("skills", [])
    max_skill_months = 0
    expert_count = 0
    expert_zero_months = 0
    for s in skills:
        dur = s.get("duration_months", 0)
        if dur > max_skill_months:
            max_skill_months = dur
        if s.get("proficiency") == "expert":
            expert_count += 1
            if dur == 0:
                expert_zero_months += 1
    
    # If they claim an expert skill but have 0 months experience in it and have many such skills
    if expert_zero_months >= 5: return True
    
    # If a skill duration is vastly larger than total career (e.g. 200 months but 5 years exp)
    if max_skill_months > (yoe * 12) + 48: # Allowing 4 years buffer for college/internships
        return True
        
    return False

def score_candidate(cand):
    profile = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    history = cand.get("career_history", [])
    
    # 1. Experience Score
    yoe = profile.get("years_of_experience", 0)
    if yoe < 3 or yoe > 15:
        return -1, "Out of experience bounds" # Disqualify outside 3-15 years
    
    # Peak at 6-8 years
    exp_score = 0
    if 5 <= yoe <= 9:
        exp_score = 100
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        exp_score = 80
    else:
        exp_score = 50
        
    # 2. Skills Score
    skills = cand.get("skills", [])
    tech_score = 0
    matched_skills = []
    
    # Also check text in career history for these keywords, some might not be explicitly in "skills" array
    all_text = (profile.get("summary", "") + " " + " ".join([h.get("description", "") for h in history])).lower()
    
    for s in skills:
        name = s.get("name", "").lower()
        if name in TARGET_SKILLS:
            matched_skills.append(name)
            weight = TARGET_SKILLS[name]
            prof = s.get("proficiency", "beginner")
            prof_mult = {"expert": 1.5, "advanced": 1.2, "intermediate": 0.8, "beginner": 0.5}.get(prof, 0.5)
            tech_score += weight * prof_mult * 10
            
    # Text mining for keywords not explicitly listed in skills
    for keyword, weight in TARGET_SKILLS.items():
        if keyword not in matched_skills and keyword in all_text:
            matched_skills.append(keyword)
            tech_score += weight * 5 # Lower weight for just mentioning it
            
    if tech_score == 0:
        return -1, "No relevant tech skills"
        
    tech_score = min(tech_score, 100) # Normalize to max 100
    
    # 3. Industry / Role Score
    industry_score = 100
    pure_services = True
    for h in history:
        comp = h.get("company", "").lower()
        if not any(sc in comp for sc in SERVICES_COMPANIES):
            pure_services = False
            break
            
    if pure_services and yoe > 0:
        industry_score = 30 # Heavy penalty for pure services
        
    # Job title penalty: if they are pure architect and don't code
    curr_title = profile.get("current_title", "").lower()
    if "architect" in curr_title or "manager" in curr_title:
        industry_score -= 20
        
    # 4. Behavioral Score
    response_rate = signals.get("recruiter_response_rate", 0.5)
    last_active = signals.get("last_active_date", "2020-01-01")
    
    # Convert string like 2024-03-12 to days ago from a fixed point so it doesn't break if run on different dates.
    # The hackathon data is likely generated in 2024. Let's use 2024-06-01 as a reference date if we can't parse or if it's too new
    # Actually, we can just do simple string comparison for "2024" or use a hardcoded reference date "2024-06-01" to be safe.
    try:
        active_date = datetime.strptime(last_active, "%Y-%m-%d")
        ref_date = datetime.strptime("2024-06-01", "%Y-%m-%d")
        days_since_active = abs((ref_date - active_date).days)
    except:
        days_since_active = 365
        
    behavior_multiplier = response_rate
    if days_since_active > 180:
        behavior_multiplier *= 0.5 # Hasn't logged in for 6 months
        
    if behavior_multiplier < 0.1:
        behavior_multiplier = 0.1
        
    # Final Score Calculation
    # Weights: Tech (50%), Exp (20%), Industry (30%)
    base_score = (tech_score * 0.6) + (exp_score * 0.2) + (industry_score * 0.2)
    final_score = base_score * behavior_multiplier
    
    # Normalize final score between 0 and 1
    final_score = final_score / 100.0
    if final_score > 1.0: final_score = 0.999
    
    # Construct Reasoning
    top_matches = ", ".join(matched_skills[:3]) if matched_skills else "general ML"
    reasoning = f"{yoe} yrs exp. Strong match in {top_matches}. "
    if pure_services:
        reasoning += "Background in services but strong tech match. "
    else:
        reasoning += "Product background. "
    reasoning += f"Engagement rate: {int(response_rate*100)}%."
    
    return final_score, reasoning

def main():
    if len(sys.argv) < 3:
        print("Usage: python ranker.py <input.jsonl> <output.csv>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Reading candidates from {input_file}...")
    
    scored_candidates = []
    
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            try:
                cand = json.loads(line)
            except:
                continue
                
            cid = cand.get("candidate_id")
            
            if is_honeypot(cand):
                continue
                
            score, reasoning = score_candidate(cand)
            if score > 0:
                scored_candidates.append((score, cid, reasoning))

    print(f"Scored {len(scored_candidates)} valid candidates. Sorting...")
    scored_candidates.sort(key=lambda x: (-x[0], x[1]))
    
    top_100 = scored_candidates[:100]
    
    print(f"Writing top 100 to {output_file}...")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        for i, (score, cid, reasoning) in enumerate(top_100):
            formatted_score = round(score, 4)
            writer.writerow([cid, i + 1, formatted_score, reasoning])
            
    print("Done!")

if __name__ == "__main__":
    main()
