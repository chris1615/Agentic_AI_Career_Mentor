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
    "skills": 0.70,
    "interests": 0.15,
    "career_goal": 0.10,
    "education": 0.05,
}

MATCH_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.72

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9.+#/-]+", _normalize(text)) if token}


def _split_user_text(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,;/\n]+", text)
    return [part.strip() for part in parts if part.strip()]


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


def _education_level_matches(user_education: str, education_level: str) -> bool:
    if not user_education or not education_level:
        return False

    normalized_education = _normalize(user_education)
    level_aliases = {
        "high school": ["12th", "higher secondary", "high school", "intermediate"],
        "diploma": ["diploma"],
        "bachelor": ["bachelor", "b.tech", "btech", "b.e", "be", "bca", "b.sc", "bsc", "ba", "b.arch", "barch", "llb"],
        "master": ["master", "m.tech", "mtech", "m.e", "me", "mca", "m.sc", "msc", "mba", "ma"],
        "professional": ["mbbs", "md", "ms", "llb", "jd", "license", "aviation", "commercial pilot"],
        "doctorate": ["phd", "doctorate"],
    }
    return any(alias in normalized_education for alias in level_aliases.get(_normalize(education_level), []))


def evaluate_education(user_education: str, role_data: dict[str, Any]) -> dict[str, Any]:
    required_degrees = role_data.get("required_degree", []) or []
    education_level = role_data.get("education_level", "")

    if not required_degrees:
        return {
            "score": 1.0,
            "status": "Eligible",
            "reason": "No mandatory degree restriction listed for this role.",
        }

    if not user_education.strip():
        return {
            "score": 0.5,
            "status": "Eligibility Unknown",
            "reason": f"Requires {', '.join(required_degrees)}, but no education details were provided.",
        }

    if _education_matches(user_education, required_degrees):
        return {
            "score": 1.0,
            "status": "Eligible",
            "reason": f"Education matches the required degree: {', '.join(required_degrees)}.",
        }

    if education_level and _education_level_matches(user_education, education_level):
        return {
            "score": 0.25,
            "status": "Not Eligible",
            "reason": (
                f"Current education level is similar, but this role specifically requires "
                f"{', '.join(required_degrees)}."
            ),
        }

    return {
        "score": 0.0,
        "status": "Not Eligible",
        "reason": f"Requires {', '.join(required_degrees)}. Current education: {user_education}.",
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

    average_skill_alignment = sum(role_skill_scores) / len(role_skill_scores)
    return matched_skills, missing_skills, average_skill_alignment


def _build_reasoning(
    *,
    matched_skills: list[str],
    missing_skills: list[str],
    role_name: str,
    role_data: dict[str, Any],
    interests: str,
    domain_similarity: float,
    career_goal: str,
    goal_similarity: float,
    education_result: dict[str, Any],
) -> list[str]:
    reasoning = []

    for skill in matched_skills[:3]:
        reasoning.append(f"✔ {skill} matches a required skill for {role_name}.")

    if interests:
        if domain_similarity >= STRONG_MATCH_THRESHOLD:
            reasoning.append(f"✔ Your interests align strongly with the {role_data.get('domain', 'target')} domain.")
        elif domain_similarity >= MATCH_THRESHOLD:
            reasoning.append(f"✔ Your interests show some alignment with the {role_data.get('domain', 'target')} domain.")
        else:
            reasoning.append(f"⚠ Your interests do not align strongly with the {role_data.get('domain', 'target')} domain.")

    if career_goal:
        if goal_similarity >= STRONG_MATCH_THRESHOLD:
            reasoning.append(f"✔ Your career goal closely matches {role_name}.")
        elif goal_similarity >= MATCH_THRESHOLD:
            reasoning.append(f"✔ Your career goal partially aligns with {role_name}.")
        else:
            reasoning.append(f"⚠ Your stated career goal is not closely aligned with {role_name}.")

    if missing_skills:
        reasoning.append(f"⚠ Missing skills: {', '.join(missing_skills[:4])}.")

    if education_result["status"] == "Eligible":
        reasoning.append(f"✔ {education_result['reason']}")
    elif education_result["status"] == "Eligibility Unknown":
        reasoning.append(f"⚠ {education_result['reason']}")
    else:
        reasoning.append(f"❌ {education_result['reason']}")

    return reasoning


def score_role(
    *,
    role_name: str,
    role_data: dict[str, Any],
    user_skills: list[str],
    interests: str,
    user_education: str,
    career_goal: str,
) -> dict[str, Any]:
    role_skills = role_data.get("skills", []) or []
    domain = role_data.get("domain", "Unknown")
    description = role_data.get("description", "")

    matched_skills, missing_skills, skill_similarity = _best_skill_matches(user_skills, role_skills)
    global_skill_similarity = semantic_similarity(", ".join(user_skills), ", ".join(role_skills))
    skill_score = (skill_similarity * 0.55) + (global_skill_similarity * 0.45)

    domain_similarity = 0.5 if not interests.strip() else semantic_similarity(interests, f"{domain}. {description}")
    goal_similarity = 0.5 if not career_goal.strip() else semantic_similarity(career_goal, f"{role_name}. {domain}. {description}")
    education_result = evaluate_education(user_education, role_data)

    final_score = (
        (skill_score * WEIGHTS["skills"])
        + (domain_similarity * WEIGHTS["interests"])
        + (goal_similarity * WEIGHTS["career_goal"])
        + (education_result["score"] * WEIGHTS["education"])
    )

    reasoning = _build_reasoning(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        role_name=role_name,
        role_data=role_data,
        interests=interests,
        domain_similarity=domain_similarity,
        career_goal=career_goal,
        goal_similarity=goal_similarity,
        education_result=education_result,
    )

    return {
        "role": role_name,
        "domain": domain,
        "description": description,
        "required_degree": role_data.get("required_degree", []),
        "education_level": role_data.get("education_level", ""),
        "career_path_steps": role_data.get("career_path_steps", []),
        "match_score": _format_percent(final_score),
        "raw_match_score": final_score,
        "eligibility_status": education_result["status"],
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reasoning_explanation": reasoning,
        "suggested_learning_path": role_data.get("career_path_steps", []),
        "score_breakdown": {
            "skill_score": _format_percent(skill_score),
            "domain_score": _format_percent(domain_similarity),
            "goal_score": _format_percent(goal_similarity),
            "education_score": _format_percent(education_result["score"]),
        },
    }


def rank_roles(
    *,
    user_skills: list[str],
    interests: str,
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
            user_education=user_education,
            career_goal=career_goal,
        )
        for role_name, role_data in roles.items()
    ]

    scored_roles.sort(key=lambda item: (-item["raw_match_score"], item["role"]))
    recommended_roles = scored_roles[:top_n]

    rejected_roles = [role for role in scored_roles[top_n:] if role["match_score"] < 50 or role["eligibility_status"] != "Eligible"]

    if career_goal.strip():
        explicit_goal_role = max(
            scored_roles,
            key=lambda role: semantic_similarity(career_goal, f"{role['role']}. {role['domain']}. {role['description']}"),
        )
        if explicit_goal_role and explicit_goal_role not in recommended_roles and explicit_goal_role not in rejected_roles:
            rejected_roles.insert(0, explicit_goal_role)

    combined_missing_skills = []
    seen = set()
    for role in recommended_roles:
        for skill in role["missing_skills"]:
            normalized = _normalize(skill)
            if normalized not in seen:
                combined_missing_skills.append(skill)
                seen.add(normalized)

    return {
        "recommended_roles": recommended_roles,
        "rejected_roles": rejected_roles[:5],
        "missing_skills": combined_missing_skills,
        "all_roles": scored_roles,
    }
