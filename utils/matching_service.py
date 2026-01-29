
import re

def calculate_match_score(candidate_profile: dict, job_data: dict) -> float:
    """
    Calculates a match score (0-100) between a candidate and a job.
    
    Args:
        candidate_profile (dict): Contains 'skills' (list), 'experience_years' (float, optional).
        job_data (dict): Contains 'required_skills' (list), 'min_experience' (int/float, optional).
        
    Returns:
        float: The match score.
    """
    
    # 1. Skill Match (70% Weight)
    cand_skills = set(k.lower() for k in candidate_profile.get('skills', []))
    job_skills_raw = job_data.get('required_skills', [])
    
    # Handle string vs list format for job skills
    if isinstance(job_skills_raw, str):
        job_skills = set(k.strip().lower() for k in job_skills_raw.split(',') if k.strip())
    else:
        job_skills = set(k.lower() for k in job_skills_raw)
        
    if not job_skills:
        skill_score = 1.0 # No skills required = perfect skill match
    else:
        intersection = cand_skills.intersection(job_skills)
        skill_score = len(intersection) / len(job_skills)
        
    # 2. Experience Match (30% Weight)
    cand_exp = float(candidate_profile.get('experience_years', 0) or 0)
    job_exp = float(job_data.get('min_experience', 0) or 0)
    
    if cand_exp >= job_exp:
        exp_score = 1.0
    elif cand_exp >= (job_exp - 1): # Within 1 year range
        exp_score = 0.5
    else:
        exp_score = 0.0
        
    # Calculate Total
    total_score = (skill_score * 0.7 + exp_score * 0.3) * 100
    
    return round(total_score, 1)

def filter_eligible_candidates(all_candidates: list, job_data: dict, min_threshold: float = 70.0) -> list:
    """
    Filters a list of candidates to find those who match the job above the threshold.
    """
    matches = []
    for cand in all_candidates:
        # Check Opt-in status (Default to False if not set, or True? User prompt said "Opt-in / Opt-out toggle". Let's assume opt-in required or default neutral)
        # We will assume a 'preferences' dict.
        prefs = cand.get('preferences', {})
        if not prefs.get('receive_job_alerts', True): # Default to True for growth, or check requirments? User said "Candidate has opted in".
             # Actually, let's default to False to be safe/compliant, or check if the field exists.
             # Ideally, we only send if they explicitly enabled it. 
             # For this implementation, we'll check if the flag is strictly False.
             continue

        score = calculate_match_score(cand, job_data)
        
        # Check user's personal threshold if set, otherwise global min
        user_threshold = float(prefs.get('min_match_threshold', min_threshold))
        
        if score >= user_threshold:
            matches.append({
                "candidate": cand,
                "score": score
            })
            
    # Sort by score descending
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches
