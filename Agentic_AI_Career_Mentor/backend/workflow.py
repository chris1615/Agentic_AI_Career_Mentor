"""
workflow.py
-----------
Orchestrates the full career mentorship pipeline.

Primary path:
    CrewAI multi-agent workflow

Fallback path:
    Deterministic local functions so the app still works without CrewAI or an
    API key.
"""

from __future__ import annotations

import os
import sys

# Ensure the backend package is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from career_agent import CareerMentorCrew, recommend_career
from data_loader import load_roles
from interview_agent import generate_interview_questions
from learning_agent import generate_learning_plan
from skill_agent import analyze_skills, get_overall_missing_skills


def _parse_user_skills(raw_skills: str) -> list[str]:
    return [skill.strip() for skill in raw_skills.split(",") if skill.strip()]


def _run_fallback_workflow(
    *,
    user_skills: list[str],
    interests: str,
    education: str,
    career_goal: str,
    roles: dict,
) -> dict:
    recommended_roles = recommend_career(
        user_skills=user_skills,
        roles=roles,
        interests=interests,
        career_goal=career_goal,
        education=education,
        top_n=3,
    )

    top_role_names = [role["role"] for role in recommended_roles]
    skill_analysis = analyze_skills(user_skills, roles)
    missing_skills = []
    seen = set()
    for role in recommended_roles:
        for skill in role.get("missing_skills", []):
            normalized_skill = skill.strip().lower()
            if normalized_skill not in seen:
                missing_skills.append(skill)
                seen.add(normalized_skill)

    if not missing_skills:
        missing_skills = get_overall_missing_skills(skill_analysis, top_role_names)
    rejected_roles = []
    learning_plan = generate_learning_plan(missing_skills)

    top_role = top_role_names[0] if top_role_names else "Software Developer"
    interview_questions = generate_interview_questions(top_role)
    interview_questions["role"] = top_role

    return {
        "status": "success",
        "engine": "fallback",
        "user_skills": user_skills,
        "recommended_roles": recommended_roles,
        "rejected_roles": rejected_roles,
        "missing_skills": missing_skills,
        "learning_plan": learning_plan,
        "interview_questions": interview_questions,
        "education": education,
        "interests": interests,
    }


def run_workflow(user_input: dict) -> dict:
    """
    Run the complete career mentorship pipeline for a given user.
    """
    raw_skills = user_input.get("skills", "").strip()
    interests = user_input.get("interests", "").strip()
    education = user_input.get("education", "").strip()
    career_goal = user_input.get("career_goal", "").strip()

    if not raw_skills:
        return {
            "status": "error",
            "message": "Please enter at least one skill to get career recommendations.",
        }

    user_skills = _parse_user_skills(raw_skills)
    if not user_skills:
        return {
            "status": "error",
            "message": "Could not parse any skills. Please separate skills with commas.",
        }

    try:
        roles = load_roles()
    except (FileNotFoundError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    crew = CareerMentorCrew(api_key=api_key)

    if crew.is_available():
        try:
            result = crew.run(
                user_skills=user_skills,
                interests=interests,
                education=education,
                career_goal=career_goal,
                roles=roles,
            )
            top_role_names = [role["role"] for role in result.get("recommended_roles", [])]
            missing_skills = result.get("missing_skills", [])
            learning_plan = generate_learning_plan(missing_skills)

            top_role = top_role_names[0] if top_role_names else "Software Developer"
            interview_questions = generate_interview_questions(top_role)
            interview_questions["role"] = top_role

            result.update(
                {
                    "status": "success",
                    "engine": "explainable-local",
                    "user_skills": user_skills,
                    "education": education,
                    "interests": interests,
                    "learning_plan": learning_plan,
                    "interview_questions": interview_questions,
                }
            )
            return result
        except Exception:
            # Fall through gracefully to the deterministic pipeline.
            pass

    try:
        return _run_fallback_workflow(
            user_skills=user_skills,
            interests=interests,
            education=education,
            career_goal=career_goal,
            roles=roles,
        )
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
