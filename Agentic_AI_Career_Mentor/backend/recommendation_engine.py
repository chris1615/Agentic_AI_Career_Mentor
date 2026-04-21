"""
recommendation_engine.py
------------------------
Core explainable ranking engine for career recommendations.
"""

from __future__ import annotations

import math
from typing import Any

from hybrid_ml import predict_role_probabilities
from semantic_engine import cosine_similarity, get_role_embedding, normalize as _normalize, semantic_similarity

WEIGHTS = {
    "skills": 0.60,
    "interests": 0.20,
    "domain": 0.10,
    "career_goal": 0.05,
    "eligibility": 0.05,
}

MATCH_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.72


def _format_percent(value: float) -> int:
    return int(round(max(0.0, min(100.0, value * 100))))


def _education_matches(user_education: str, required_degrees: list[str]) -> bool:
    normalized_education = _normalize(user_education)
    return any(_normalize(degree) in normalized_education for degree in required_degrees)


def evaluate_eligibility(user_education: str, role_data: dict[str, Any], missing_skills: list[str]) -> dict[str, Any]:
    role_domain = role_data.get("domain", "target domain")
    degree_required = bool(role_data.get("degree_required", False))
    portfolio_required = bool(role_data.get("portfolio_required", False))
    required_degrees = role_data.get("required_degree", []) or []

    reasons = []

    if not degree_required:
        reasons.append("✔ This role does not require a strict degree.")
        if portfolio_required:
            reasons.append("⚠ Portfolio quality matters more than formal degree requirements for this role.")
        if missing_skills:
            reasons.append(f"⚠ Main improvement areas: {', '.join(missing_skills[:3])}.")
        return {
            "score": 1.0,
            "status": "Eligible",
            "reasons": reasons,
        }

    if not user_education.strip():
        reasons.append(f"⚠ This role expects {', '.join(required_degrees) or 'a relevant degree'}, but no education was provided.")
        return {
            "score": 0.5,
            "status": "Eligibility Unknown",
            "reasons": reasons,
        }

    if _education_matches(user_education, required_degrees):
        reasons.append(f"✔ Degree matches the accepted requirement: {', '.join(required_degrees)}.")
        reasons.append(f"✔ Your background supports entry into the {role_domain} domain.")
        return {
            "score": 1.0,
            "status": "Eligible",
            "reasons": reasons,
        }

    reasons.append(f"❌ Requires {', '.join(required_degrees)}.")
    reasons.append(f"❌ Current degree: {user_education}.")
    if missing_skills:
        reasons.append(f"⚠ Missing background areas include {', '.join(missing_skills[:2])}.")
    return {
        "score": 0.0,
        "status": "Not Eligible",
        "reasons": reasons,
    }


def _best_skill_matches(user_skills: list[str], role_skills: list[str]) -> tuple[list[str], list[str], float]:
    if not role_skills:
        return [], [], 0.0

    matched_skills = []
    missing_skills = []
    role_skill_scores = []

    for role_skill in role_skills:
        best_similarity = 0.0
        for user_skill in user_skills:
            similarity = semantic_similarity(user_skill, role_skill)
            if similarity > best_similarity:
                best_similarity = similarity

        role_skill_scores.append(best_similarity)
        if best_similarity >= MATCH_THRESHOLD:
            matched_skills.append(role_skill)
        else:
            missing_skills.append(role_skill)

    return matched_skills, missing_skills, sum(role_skill_scores) / len(role_skill_scores)


def _role_semantic_score(user_skills: list[str], role_name: str, role_data: dict[str, Any]) -> float:
    role_embedding = get_role_embedding(role_name, role_data)
    user_text = ", ".join(user_skills)
    user_embedding = get_role_embedding(
        f"user::{user_text}",
        {
            "skills": user_skills,
            "domain": role_data.get("domain", ""),
            "description": "",
        },
    )
    if role_embedding is None or user_embedding is None:
        return semantic_similarity(user_text, ", ".join(role_data.get("skills", []) or []))

    similarity = cosine_similarity(user_embedding, role_embedding)
    return max(0.0, min(1.0, similarity))


def _domain_similarity(interests: str, interest_domains: list[str], role_domain: str, description: str) -> float:
    scores = []
    if interests.strip():
        scores.append(semantic_similarity(interests, f"{role_domain}. {description}"))
    if interest_domains:
        scores.append(max(semantic_similarity(domain, role_domain) for domain in interest_domains))
    return sum(scores) / len(scores) if scores else 0.5


def _build_reasoning(
    *,
    role_name: str,
    domain: str,
    matched_skills: list[str],
    missing_skills: list[str],
    interests_score: float,
    domain_score: float,
    goal_score: float,
    eligibility_result: dict[str, Any],
    portfolio_required: bool,
) -> list[str]:
    reasoning = []

    if matched_skills:
        for skill in matched_skills[:3]:
            reasoning.append(f"✔ {skill} matches a required skill.")
    else:
        reasoning.append(f"⚠ You currently have few direct skill matches for {role_name}.")

    if interests_score >= MATCH_THRESHOLD:
        reasoning.append("✔ Your stated interests support this career direction.")
    else:
        reasoning.append("⚠ Your stated interests only weakly support this role.")

    if domain_score >= MATCH_THRESHOLD:
        reasoning.append(f"✔ Your interests map well to the {domain} domain.")
    else:
        reasoning.append(f"⚠ Your interests do not strongly map to the {domain} domain.")

    if goal_score >= MATCH_THRESHOLD:
        reasoning.append(f"✔ Your career goal aligns with {role_name}.")
    else:
        reasoning.append(f"⚠ Your career goal has limited influence for {role_name} because stronger skill or domain matches exist elsewhere.")

    for skill in missing_skills[:3]:
        reasoning.append(f"⚠ Missing skill: {skill}.")

    if portfolio_required:
        reasoning.append("⚠ This role is portfolio-driven, so practical projects matter strongly.")

    reasoning.extend(eligibility_result["reasons"])
    return reasoning


def score_role(
    *,
    role_name: str,
    role_data: dict[str, Any],
    user_skills: list[str],
    interests: str,
    interest_domains: list[str],
    user_education: str,
    career_goal: str,
    rf_probability: float = 0.0,
) -> dict[str, Any]:
    role_skills = role_data.get("skills", []) or []
    domain = role_data.get("domain", "Unknown")
    description = role_data.get("description", "")
    portfolio_required = bool(role_data.get("portfolio_required", False))

    matched_skills, missing_skills, skill_similarity = _best_skill_matches(user_skills, role_skills)
    global_skill_similarity = semantic_similarity(", ".join(user_skills), ", ".join(role_skills))
    role_semantic_score = _role_semantic_score(user_skills, role_name, role_data)
    semantic_score = (skill_similarity * 0.35) + (global_skill_similarity * 0.30) + (role_semantic_score * 0.35)
    skill_score = semantic_score
    interests_score = 0.5 if not interests.strip() else semantic_similarity(interests, f"{description}. {domain}. {' '.join(role_skills)}")
    domain_score = _domain_similarity(interests, interest_domains, domain, description)
    goal_score = 0.5 if not career_goal.strip() else semantic_similarity(career_goal, f"{role_name}. {domain}. {description}")
    eligibility_result = evaluate_eligibility(user_education, role_data, missing_skills)

    existing_weighted_score = (
        (skill_score * WEIGHTS["skills"])
        + (interests_score * WEIGHTS["interests"])
        + (domain_score * WEIGHTS["domain"])
        + (goal_score * WEIGHTS["career_goal"])
        + (eligibility_result["score"] * WEIGHTS["eligibility"])
    )
    final_score = (semantic_score * 0.50) + (rf_probability * 0.30) + (existing_weighted_score * 0.20)

    return {
        "role": role_name,
        "domain": domain,
        "description": description,
        "required_degree": role_data.get("required_degree", []),
        "degree_required": bool(role_data.get("degree_required", False)),
        "portfolio_required": portfolio_required,
        "education_level": role_data.get("education_level", ""),
        "roadmap": role_data.get("roadmap", []),
        "match_score": _format_percent(final_score),
        "confidence_score": _format_percent(final_score),
        "raw_match_score": final_score,
        "eligibility_status": eligibility_result["status"],
        "eligibility_reasoning": eligibility_result["reasons"],
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reasoning_explanation": _build_reasoning(
            role_name=role_name,
            domain=domain,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            interests_score=interests_score,
            domain_score=domain_score,
            goal_score=goal_score,
            eligibility_result=eligibility_result,
            portfolio_required=portfolio_required,
        ),
        "score_breakdown": {
            "skill_score": _format_percent(skill_score),
            "semantic_score": _format_percent(semantic_score),
            "random_forest_score": _format_percent(rf_probability),
            "existing_weighted_score": _format_percent(existing_weighted_score),
            "interest_score": _format_percent(interests_score),
            "domain_score": _format_percent(domain_score),
            "goal_score": _format_percent(goal_score),
            "eligibility_score": _format_percent(eligibility_result["score"]),
        },
    }


def rank_roles(
    *,
    user_skills: list[str],
    interests: str,
    interest_domains: list[str],
    user_education: str,
    career_goal: str,
    roles: dict[str, Any],
    top_n: int = 3,
) -> dict[str, Any]:
    rf_probabilities, model_metadata = predict_role_probabilities(
        user_skills=user_skills,
        interests=interests,
        career_goal=career_goal,
        roles=roles,
    )

    scored_roles = [
        score_role(
            role_name=role_name,
            role_data=role_data,
            user_skills=user_skills,
            interests=interests,
            interest_domains=interest_domains,
            user_education=user_education,
            career_goal=career_goal,
            rf_probability=rf_probabilities.get(role_name, 0.0),
        )
        for role_name, role_data in roles.items()
    ]

    scored_roles.sort(key=lambda item: (-item["raw_match_score"], item["role"]))
    recommended_roles = scored_roles[:top_n]
    rejected_roles = [role for role in scored_roles[top_n:] if role["match_score"] < 50 or role["eligibility_status"] != "Eligible"]

    if career_goal.strip() and scored_roles:
        explicit_goal_role = max(
            scored_roles,
            key=lambda role: semantic_similarity(career_goal, f"{role['role']}. {role['domain']}. {role['description']}"),
        )
        if explicit_goal_role not in recommended_roles and explicit_goal_role not in rejected_roles:
            rejected_roles.insert(0, explicit_goal_role)

    return {
        "recommended_roles": recommended_roles,
        "rejected_roles": rejected_roles[:5],
        "all_roles": scored_roles,
        "ml_model_metrics": model_metadata,
    }
