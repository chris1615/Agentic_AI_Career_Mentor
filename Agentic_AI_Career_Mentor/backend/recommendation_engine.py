"""
recommendation_engine.py
------------------------
Core explainable ranking engine for career recommendations.
"""

from __future__ import annotations

import math
import re
from typing import Any

WEIGHTS = {
    "skills": 0.60,
    "interests": 0.20,
    "domain": 0.10,
    "career_goal": 0.05,
    "eligibility": 0.05,
}

MATCH_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.72

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9.+#/-]+", _normalize(text)) if token}


def _load_sentence_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED

    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = None

    return _MODEL


def _cosine_similarity(vec_a, vec_b) -> float:
    numerator = sum(a * b for a, b in zip(vec_a, vec_b))
    denom_a = math.sqrt(sum(a * a for a in vec_a))
    denom_b = math.sqrt(sum(b * b for b in vec_b))
    if denom_a == 0 or denom_b == 0:
        return 0.0
    return numerator / (denom_a * denom_b)


def _fallback_similarity(text_a: str, text_b: str) -> float:
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / math.sqrt(len(tokens_a) * len(tokens_b))


def semantic_similarity(text_a: str, text_b: str) -> float:
    text_a = (text_a or "").strip()
    text_b = (text_b or "").strip()

    if not text_a or not text_b:
        return 0.0
    if _normalize(text_a) == _normalize(text_b):
        return 1.0

    model = _load_sentence_model()
    if model is None:
        return max(0.0, min(1.0, _fallback_similarity(text_a, text_b)))

    try:
        embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
        similarity = float(_cosine_similarity(embeddings[0], embeddings[1]))
        return max(0.0, min(1.0, similarity))
    except Exception:
        return max(0.0, min(1.0, _fallback_similarity(text_a, text_b)))


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
) -> dict[str, Any]:
    role_skills = role_data.get("skills", []) or []
    domain = role_data.get("domain", "Unknown")
    description = role_data.get("description", "")
    portfolio_required = bool(role_data.get("portfolio_required", False))

    matched_skills, missing_skills, skill_similarity = _best_skill_matches(user_skills, role_skills)
    global_skill_similarity = semantic_similarity(", ".join(user_skills), ", ".join(role_skills))
    skill_score = (skill_similarity * 0.55) + (global_skill_similarity * 0.45)
    interests_score = 0.5 if not interests.strip() else semantic_similarity(interests, f"{description}. {domain}. {' '.join(role_skills)}")
    domain_score = _domain_similarity(interests, interest_domains, domain, description)
    goal_score = 0.5 if not career_goal.strip() else semantic_similarity(career_goal, f"{role_name}. {domain}. {description}")
    eligibility_result = evaluate_eligibility(user_education, role_data, missing_skills)

    final_score = (
        (skill_score * WEIGHTS["skills"])
        + (interests_score * WEIGHTS["interests"])
        + (domain_score * WEIGHTS["domain"])
        + (goal_score * WEIGHTS["career_goal"])
        + (eligibility_result["score"] * WEIGHTS["eligibility"])
    )

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
    scored_roles = [
        score_role(
            role_name=role_name,
            role_data=role_data,
            user_skills=user_skills,
            interests=interests,
            interest_domains=interest_domains,
            user_education=user_education,
            career_goal=career_goal,
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
    }
