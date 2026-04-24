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
from job_api import fetch_live_jobs_for_roles, jobs_to_role_catalog
from learning_agent import generate_learning_plan
from semantic_engine import warm_role_embeddings


def _parse_user_skills(raw_skills: str) -> list[str]:
    return [skill.strip() for skill in raw_skills.split(",") if skill.strip()]


def _roles_to_dict(roles: list[dict] | dict) -> dict[str, dict]:
    if isinstance(roles, dict):
        return {str(role_name): dict(role_data) for role_name, role_data in roles.items()}
    normalized = {}
    for index, role in enumerate(roles):
        role_name = role.get("role", f"role_{index}")
        normalized[role_name] = dict(role)
    return normalized


def _merge_roles(static_roles: list[dict] | dict, dynamic_roles: dict) -> dict:
    merged = _roles_to_dict(static_roles)
    for role_name, role_data in dynamic_roles.items():
        if role_name not in merged:
            role_copy = dict(role_data)
            role_copy.setdefault("static_dataset_skills", [])
            role_copy.setdefault("dynamic_learned_skills", list(role_copy.get("required_skills", []) or role_copy.get("skills", [])))
            merged[role_name] = role_copy
            continue

        existing = dict(merged[role_name])
        incoming = dict(role_data)
        static_skills = list(existing.get("required_skills") or existing.get("skills") or [])
        learned_skills = list(
            incoming.get("dynamic_learned_skills")
            or incoming.get("required_skills")
            or incoming.get("skills")
            or []
        )
        merged_skills = []
        seen = set()
        for skill in static_skills + learned_skills:
            key = skill.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged_skills.append(skill)

        existing["required_skills"] = merged_skills
        existing["skills"] = merged_skills
        existing["static_dataset_skills"] = static_skills
        existing["dynamic_learned_skills"] = learned_skills
        existing["skill_weights"] = incoming.get("skill_weights", existing.get("skill_weights", {}))
        existing["skill_clusters"] = incoming.get("skill_clusters", existing.get("skill_clusters", []))
        existing["job_count"] = max(int(existing.get("job_count", 0)), int(incoming.get("job_count", 0)))
        existing["live_job_confidence_contribution"] = incoming.get(
            "live_job_confidence_contribution",
            existing.get("live_job_confidence_contribution", 0),
        )
        existing["sources"] = incoming.get("sources", existing.get("sources", []))
        if incoming.get("description"):
            existing["description"] = incoming["description"]
        if incoming.get("role_text"):
            existing["role_text"] = incoming["role_text"]
        merged[role_name] = existing
    return merged


def _select_primary_roles(static_roles: list[dict] | dict, live_roles: dict) -> tuple[dict, str]:
    if live_roles:
        return _roles_to_dict(live_roles), "live_job_market"
    if static_roles:
        return _roles_to_dict(static_roles), "static_dataset_fallback"
    return {}, "unavailable"


def _attach_role_learning_plans(recommended_roles: list[dict], roles: dict) -> None:
    role_lookup = _roles_to_dict(roles)
    for role in recommended_roles:
        role_data = role_lookup.get(role["role"], {})
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
    except (FileNotFoundError, ValueError):
        static_roles = []

    discovery = discover_dynamic_roles(user_skills, interests, career_goal)
    interest_domains = discovery.get("interest_domains", [])
    live_job_listings = discovery.get("live_job_listings", [])
    live_roles = discovery.get("roles", {})
    live_fetch_succeeded = bool(live_job_listings) or bool(live_roles)
    roles, role_source = _select_primary_roles(static_roles, live_roles)
    if not roles:
        return {
            "status": "error",
            "message": "No live roles or fallback dataset roles are available. Configure a job API or add a role dataset.",
        }

    warm_role_embeddings(roles)

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

    recommended_role_names = [role.get("role", "") for role in result.get("recommended_roles", []) if role.get("role")]
    api_job_listings = fetch_live_jobs_for_roles(recommended_role_names)
    merged_live_jobs = []
    seen_jobs = set()
    for job in live_job_listings + api_job_listings:
        dedupe_key = (
            (job.get("role") or "").strip().lower(),
            (job.get("company") or "").strip().lower(),
            (job.get("location") or "").strip().lower(),
        )
        if dedupe_key in seen_jobs:
            continue
        seen_jobs.add(dedupe_key)
        merged_live_jobs.append(job)

    live_role_catalog = jobs_to_role_catalog(merged_live_jobs)
    if live_role_catalog:
        roles = _merge_roles(live_role_catalog, roles)

    recommended_roles = result.get("recommended_roles", [])
    if not recommended_roles:
        return {
            "status": "error",
            "message": "No matching roles could be generated for this profile.",
        }

    selected_role = recommended_roles[0]
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
        "career_goal": career_goal,
        "interest_domains": interest_domains,
        "recommended_roles": result.get("recommended_roles", []),
        "rejected_roles": result.get("rejected_roles", []),
        "ml_model_metrics": result.get("ml_model_metrics", {}),
        "selected_role": selected_role_name,
        "missing_skills": top_role_missing_skills,
        "learning_plan": top_role_plan,
        "interview_questions": interview_questions,
        "live_job_listings": merged_live_jobs,
        "dynamic_role_count": len(discovery.get("roles", {})),
        "role_data_source": role_source,
        "live_fetch_succeeded": live_fetch_succeeded,
        "live_fetch_fallback_used": role_source == "static_dataset_fallback",
        "live_role_query": discovery.get("query", ""),
        "live_role_count": discovery.get("live_role_count", len(live_roles)),
        "live_skill_clusters": discovery.get("skill_clusters", []),
        "live_catalog_updated_at": discovery.get("updated_at"),
        "hybrid_components": {
            "semantic_matching": "sentence-transformers/all-MiniLM-L6-v2",
            "random_forest": "enabled",
            "existing_weighted_score": "enabled",
            "live_job_ingestion": "primary",
        },
    }
