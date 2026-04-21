"""
workflow.py
-----------
Orchestrates the full career mentorship pipeline.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from career_agent import CareerMentorCrew, recommend_career
from data_loader import load_roles
from dynamic_role_agent import discover_dynamic_roles
from interview_agent import generate_interview_questions
from learning_agent import generate_learning_plan


def _parse_user_skills(raw_skills: str) -> list[str]:
    return [skill.strip() for skill in raw_skills.split(",") if skill.strip()]


def _merge_roles(static_roles: dict, dynamic_roles: dict) -> dict:
    merged = dict(static_roles)
    for role_name, role_data in dynamic_roles.items():
        if role_name not in merged:
            merged[role_name] = role_data
    return merged


def _attach_role_learning_plans(recommended_roles: list[dict], roles: dict) -> None:
    for role in recommended_roles:
        role_data = roles.get(role["role"], {})
        role["learning_plan"] = generate_learning_plan(
            role.get("missing_skills", []),
            role_name=role["role"],
            role_data=role_data,
        )


def run_workflow(user_input: dict) -> dict:
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
        static_roles = load_roles()
    except (FileNotFoundError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}

    discovery = discover_dynamic_roles(user_skills, interests, career_goal)
    interest_domains = discovery.get("interest_domains", [])
    live_job_listings = discovery.get("live_job_listings", [])
    roles = _merge_roles(static_roles, discovery.get("roles", {}))

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    crew = CareerMentorCrew(api_key=api_key)

    try:
        result = crew.run(
            user_skills=user_skills,
            interests=interests,
            interest_domains=interest_domains,
            education=education,
            career_goal=career_goal,
            roles=roles,
        )
    except Exception as exc:
        try:
            recommended_roles = recommend_career(
                user_skills=user_skills,
                roles=roles,
                interests=interests,
                interest_domains=interest_domains,
                career_goal=career_goal,
                education=education,
                top_n=3,
            )
            result = {
                "recommended_roles": recommended_roles,
                "rejected_roles": [],
                "all_roles": recommended_roles,
                "engine": "fallback",
                "fallback_error": str(exc),
            }
        except ValueError as inner_exc:
            return {"status": "error", "message": str(inner_exc)}

    _attach_role_learning_plans(result.get("recommended_roles", []), roles)

    selected_role = result.get("recommended_roles", [{}])[0]
    selected_role_name = selected_role.get("role", "Software Developer")
    top_role_plan = selected_role.get("learning_plan", [])
    top_role_missing_skills = selected_role.get("missing_skills", [])

    interview_questions = generate_interview_questions(selected_role_name)
    interview_questions["role"] = selected_role_name

    return {
        "status": "success",
        "engine": result.get("engine", "hybrid-dynamic"),
        "user_skills": user_skills,
        "education": education,
        "interests": interests,
        "interest_domains": interest_domains,
        "recommended_roles": result.get("recommended_roles", []),
        "rejected_roles": result.get("rejected_roles", []),
        "selected_role": selected_role_name,
        "missing_skills": top_role_missing_skills,
        "learning_plan": top_role_plan,
        "interview_questions": interview_questions,
        "live_job_listings": live_job_listings,
        "dynamic_role_count": len(discovery.get("roles", {})),
    }
