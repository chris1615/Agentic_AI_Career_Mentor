"""
workflow.py
-----------
Orchestrates the full multi-agent career mentorship pipeline.

Pipeline:
    Skill Analyzer Agent
        → Career Advisor Agent
            → Learning Planner Agent
                → Interview Preparation Agent

Each agent feeds its output into the next, producing a combined result
that the frontend can display directly.
"""

import sys
import os

# Ensure the backend package is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_roles
from skill_agent import analyze_skills, get_overall_missing_skills
from career_agent import recommend_career
from learning_agent import generate_learning_plan
from interview_agent import generate_interview_questions


def run_workflow(user_input: dict) -> dict:
    """
    Run the complete career mentorship pipeline for a given user.

    Args:
        user_input: A dictionary with the following keys:
            - skills       (str)  : comma-separated skills, e.g. "Python, SQL"
            - interests    (str)  : free-text interests, e.g. "AI, data"
            - education    (str)  : optional education background
            - career_goal  (str)  : optional career goal description

    Returns:
        A structured result dictionary:
        {
            "status": "success" | "error",
            "message": str,                  # error detail (only on error)
            "recommended_roles": [           # top-3 career recommendations
                {
                    "role": str,
                    "domain": str,
                    "match_score": float,
                    "matched_skills": list[str],
                    "missing_skills": list[str],
                    "description": str,
                }
            ],
            "missing_skills": list[str],     # aggregated across top roles
            "learning_plan": [               # weekly roadmap
                {
                    "week": int,
                    "skill": str,
                    "steps": list[str],
                    "resource_hint": str,
                }
            ],
            "interview_questions": {         # for the #1 recommended role
                "role": str,
                "technical": list[str],
                "behavioral": list[str],
            },
        }
    """
    # ------------------------------------------------------------------
    # 0. Validate and parse user input
    # ------------------------------------------------------------------
    raw_skills = user_input.get("skills", "").strip()
    interests = user_input.get("interests", "").strip()
    education = user_input.get("education", "").strip()
    career_goal = user_input.get("career_goal", "").strip()

    if not raw_skills:
        return {
            "status": "error",
            "message": "Please enter at least one skill to get career recommendations.",
        }

    # Parse comma-separated skills, filtering out blanks
    user_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    if not user_skills:
        return {
            "status": "error",
            "message": "Could not parse any skills. Please separate skills with commas.",
        }

    # ------------------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------------------
    try:
        roles = load_roles()
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # 2. AGENT 1 — Skill Analyzer
    # ------------------------------------------------------------------
    try:
        skill_analysis = analyze_skills(user_skills, roles)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # 3. AGENT 2 — Career Advisor
    # ------------------------------------------------------------------
    try:
        recommended_roles = recommend_career(
            user_skills=user_skills,
            roles=roles,
            interests=interests,
            career_goal=career_goal,
            top_n=3,
        )
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    top_role_names = [r["role"] for r in recommended_roles]

    # ------------------------------------------------------------------
    # 4. AGENT 3 — Learning Planner
    # ------------------------------------------------------------------
    missing_skills = get_overall_missing_skills(skill_analysis, top_role_names)
    learning_plan = generate_learning_plan(missing_skills)

    # ------------------------------------------------------------------
    # 5. AGENT 4 — Interview Preparation
    # ------------------------------------------------------------------
    top_role = top_role_names[0] if top_role_names else "Software Developer"
    interview_questions = generate_interview_questions(top_role)
    interview_questions["role"] = top_role

    # ------------------------------------------------------------------
    # 6. Combine and return
    # ------------------------------------------------------------------
    return {
        "status": "success",
        "user_skills": user_skills,
        "recommended_roles": recommended_roles,
        "missing_skills": missing_skills,
        "learning_plan": learning_plan,
        "interview_questions": interview_questions,
        "education": education,
        "interests": interests,
    }
