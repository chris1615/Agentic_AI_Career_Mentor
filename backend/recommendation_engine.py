"""
recommendation_engine.py
------------------------
Ranks career roles using semantic similarity, normalized skill overlap,
interest alignment, and live job market signals.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from backend.domain_engine import detect_domain, get_domain_penalty
from backend.semantic_engine import cosine_similarity, encode_text, fallback_similarity
from backend.skill_normalizer import analyze_skill_relationships, normalize_skill_list

logger = logging.getLogger(__name__)


def _similarity(text_a: str, text_b: str) -> float:
    if not text_a.strip() or not text_b.strip():
        return 0.0
    embedding_a = encode_text(text_a)
    embedding_b = encode_text(text_b)
    if embedding_a is not None and embedding_b is not None:
        return max(0.0, min(1.0, cosine_similarity(embedding_a, embedding_b)))
    return max(0.0, min(1.0, fallback_similarity(text_a, text_b)))


def rank_roles(
    user_profile: dict[str, Any],
    roles: list[dict[str, Any]],
    rf_model: Any = None,
) -> list[dict[str, Any]]:
    normalized_user_skills = normalize_skill_list(user_profile.get("skills", []))
    skills_text = " ".join(normalized_user_skills)
    interests_text = " ".join(user_profile.get("interests", []))
    goal_text = user_profile.get("goal", "")

    user_domain = detect_domain(
        user_profile.get("skills", []),
        user_profile.get("interests", []),
    )

    scored: list[dict[str, Any]] = []

    for role in roles:
        role_skills = list(role.get("required_skills", []))
        normalized_role_skills = normalize_skill_list(role_skills)
        role_skills_text = " ".join(normalized_role_skills)
        role_desc_text = role.get("description", "")
        role_domain = role.get("domain", "General")
        role_text = role.get(
            "role_text",
            f"{role.get('role', '')}. {role_desc_text}. Skills: {role_skills_text}",
        )

        match_analysis = analyze_skill_relationships(
            user_profile.get("skills", []),
            role_skills,
            semantic_threshold=0.6,
        )
        overlap_score = float(match_analysis["overlap_score"])
        role_skill_weights = role.get("skill_weights", {}) or {}
        weighted_match_numerator = 0.0
        weighted_match_denominator = 0.0
        matched_skill_keys = {skill.lower() for skill in match_analysis["matched_skills"]}
        for skill in role_skills:
            weight = float(role_skill_weights.get(skill, role_skill_weights.get(skill.lower(), 1.0)))
            weighted_match_denominator += weight
            if skill.lower() in matched_skill_keys:
                weighted_match_numerator += weight
        weighted_overlap_score = (
            weighted_match_numerator / weighted_match_denominator
            if weighted_match_denominator > 0
            else overlap_score
        )
        skill_sim = _similarity(skills_text, role_skills_text or role_text)

        if rf_model is not None:
            try:
                feature_vec = np.array([skill_sim, overlap_score]).reshape(1, -1)
                rf_prob = float(rf_model.predict_proba(feature_vec)[0][1])
            except Exception:
                rf_prob = ((skill_sim + weighted_overlap_score) / 2.0) * 0.8
        else:
            rf_prob = ((skill_sim + weighted_overlap_score) / 2.0) * 0.8

        interest_sim = _similarity(interests_text, role_text)
        goal_sim = _similarity(goal_text, role_text)

        raw_score = (
            0.35 * skill_sim
            + 0.25 * weighted_overlap_score
            + 0.15 * rf_prob
            + 0.15 * interest_sim
            + 0.10 * goal_sim
        )
        market_signal = min(float(role.get("job_count", 0)) / 8.0, 1.0)
        live_job_bonus = 0.12 * market_signal
        raw_score = min(raw_score + live_job_bonus, 1.0)

        penalty = get_domain_penalty(role_domain, user_domain)
        final_score = raw_score * penalty

        confidence = round(min(final_score * 100, 100), 1)
        if match_analysis["matched_skills"] and confidence < 35 and (
            skill_sim >= 0.45 or match_analysis["semantic_matches"] or match_analysis["inferred_matches"]
        ):
            confidence = 35.0

        eligibility = (
            "Eligible" if confidence >= 60
            else "Partially Eligible" if confidence >= 35
            else "Not Eligible"
        )

        scored.append(
            {
                **role,
                "confidence_score": confidence,
                "eligibility_status": eligibility,
                "user_domain": user_domain,
                "_match_analysis": match_analysis,
                "_debug": {
                    "skill_sim": round(skill_sim, 3),
                    "overlap_score": round(overlap_score, 3),
                    "weighted_overlap_score": round(weighted_overlap_score, 3),
                    "rf_prob": round(rf_prob, 3),
                    "interest_sim": round(interest_sim, 3),
                    "goal_sim": round(goal_sim, 3),
                    "market_signal": round(market_signal, 3),
                    "live_job_bonus": round(live_job_bonus, 3),
                    "domain_penalty": penalty,
                },
            }
        )

    scored.sort(key=lambda r: r["confidence_score"], reverse=True)
    return scored
