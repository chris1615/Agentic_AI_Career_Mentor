"""
career_agent.py
---------------
Career recommendation helpers and a backend-compatible agent wrapper.
"""

from __future__ import annotations

from typing import Any

try:
    from backend.recommendation_engine import rank_roles
    from backend.skill_normalizer import format_skill_label
except ImportError:
    from recommendation_engine import rank_roles
    from skill_normalizer import format_skill_label


def _role_skills(role_data: dict[str, Any]) -> list[str]:
    return list(role_data.get("required_skills") or role_data.get("skills") or [])


def _roles_as_list(roles: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(roles, list):
        normalized = []
        for role in roles:
            role_copy = dict(role)
            role_copy["required_skills"] = _role_skills(role_copy)
            normalized.append(role_copy)
        return normalized

    normalized = []
    for role_name, role_data in roles.items():
        role_copy = dict(role_data)
        role_copy.setdefault("role", role_name)
        role_copy["required_skills"] = _role_skills(role_copy)
        normalized.append(role_copy)
    return normalized


def _pretty_list(values: list[str]) -> list[str]:
    return [format_skill_label(value) for value in values]


def _build_role_explanation(role: dict[str, Any], user_skills: list[str]) -> dict[str, Any]:
    required_skills = _role_skills(role)
    match_analysis = role.get("_match_analysis", {}) or {}
    confidence_score = float(role.get("confidence_score", 0.0))
    debug = role.get("_debug", {}) or {}

    direct_matches = _pretty_list(match_analysis.get("direct_matches", []))
    alias_matches = _pretty_list(match_analysis.get("alias_matches", []))
    inferred_matches = _pretty_list(match_analysis.get("inferred_matches", []))
    semantic_matches = _pretty_list(match_analysis.get("semantic_matches", []))
    missing_skills = _pretty_list(match_analysis.get("missing_skills", []))
    normalized_user_skills = _pretty_list(match_analysis.get("normalized_user_skills", []))
    inferred_user_skills = _pretty_list(match_analysis.get("inferred_user_skills", []))

    matched_skills = direct_matches + alias_matches + inferred_matches + semantic_matches
    match_score = round(float(match_analysis.get("overlap_score", 0.0)) * 100, 1) if required_skills else 0.0

    if role.get("eligibility_status") == "Not Eligible" and (semantic_matches or inferred_matches or alias_matches):
        role["eligibility_status"] = "Partially Eligible"

    role["matched_skills"] = matched_skills
    role["direct_matches"] = direct_matches
    role["alias_matches"] = alias_matches
    role["inferred_matches"] = inferred_matches
    role["semantic_matches"] = semantic_matches
    role["normalized_user_skills"] = normalized_user_skills
    role["inferred_user_skills"] = inferred_user_skills
    role["missing_skills"] = missing_skills
    role["static_dataset_skills"] = role.get("static_dataset_skills", [])
    role["dynamic_learned_skills"] = role.get("dynamic_learned_skills", [])
    role["skill_clusters"] = role.get("skill_clusters", [])
    role["match_score"] = match_score
    role["reasoning_explanation"] = [
        f"Direct matches: {len(direct_matches)}.",
        f"Alias matches: {len(alias_matches)}.",
        f"Inferred base-skill matches: {len(inferred_matches)}.",
        f"Semantic matches: {len(semantic_matches)}.",
        f"Static dataset skills used: {len(role.get('static_dataset_skills', []))}.",
        f"Dynamically learned skills used: {len(role.get('dynamic_learned_skills', []))}.",
        f"Live job market contribution: {round(float(debug.get('live_job_bonus', 0.0)) * 100, 1)}%.",
        f"Detected user domain: {role.get('user_domain', 'General')}.",
        f"Role domain: {role.get('domain', 'General')}.",
    ]
    role["eligibility_reasoning"] = [
        f"Overall confidence score: {confidence_score}%.",
        f"Eligibility status: {role.get('eligibility_status', 'Unknown')}.",
        f"Normalized user skills considered: {', '.join(normalized_user_skills[:8]) or 'None'}.",
    ]
    role["score_breakdown"] = {
        "skill_score": round(float(debug.get("skill_sim", 0.0)) * 100, 1),
        "semantic_score": round(float(debug.get("skill_sim", 0.0)) * 100, 1),
        "overlap_score": round(float(debug.get("overlap_score", 0.0)) * 100, 1),
        "weighted_overlap_score": round(float(debug.get("weighted_overlap_score", 0.0)) * 100, 1),
        "random_forest_score": round(float(debug.get("rf_prob", 0.0)) * 100, 1),
        "existing_weighted_score": round(confidence_score, 1),
        "interest_score": round(float(debug.get("interest_sim", 0.0)) * 100, 1),
        "domain_score": round(float(debug.get("domain_penalty", 0.0)) * 100, 1),
        "goal_score": round(float(debug.get("goal_sim", 0.0)) * 100, 1),
        "market_signal_score": round(float(debug.get("market_signal", 0.0)) * 100, 1),
        "live_job_bonus_score": round(float(debug.get("live_job_bonus", 0.0)) * 100, 1),
        "eligibility_score": round(confidence_score, 1),
    }
    return role


def recommend_career(
    user_skills: list[str],
    roles: dict[str, Any],
    interests: str = "",
    interest_domains: list[str] | None = None,
    career_goal: str = "",
    education: str = "",
    top_n: int = 3,
) -> list[dict[str, Any]]:
    if not user_skills:
        raise ValueError("User skills list is empty. Please enter at least one skill.")

    normalized_roles = _roles_as_list(roles)
    scored_roles = rank_roles(
        user_profile={
            "skills": user_skills,
            "interests": [interests, *list(interest_domains or [])],
            "goal": career_goal,
            "education": education,
        },
        roles=normalized_roles,
    )
    return [_build_role_explanation(role, user_skills) for role in scored_roles[:top_n]]


class CareerMentorCrew:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return True

    def run(
        self,
        *,
        user_skills: list[str],
        interests: str,
        interest_domains: list[str],
        education: str,
        career_goal: str,
        roles: dict[str, Any],
    ) -> dict[str, Any]:
        all_roles = recommend_career(
            user_skills=user_skills,
            roles=roles,
            interests=interests,
            interest_domains=interest_domains,
            career_goal=career_goal,
            education=education,
            top_n=max(3, len(roles) if isinstance(roles, list) else len(roles.keys())),
        )
        recommended_roles = all_roles[:3]
        rejected_roles = [role for role in all_roles[3:] if role.get("confidence_score", 0) < 60]
        return {
            "recommended_roles": recommended_roles,
            "rejected_roles": rejected_roles,
            "all_roles": all_roles,
            "engine": "local-hybrid",
            "ml_model_metrics": {},
        }
