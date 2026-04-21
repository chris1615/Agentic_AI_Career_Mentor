"""
career_agent.py
---------------
Career recommendation helpers and a backend-compatible agent wrapper.
"""

from __future__ import annotations

from typing import Any

from recommendation_engine import rank_roles


def recommend_career(
    user_skills: list[str],
    roles: dict[str, Any],
    interests: str = "",
    career_goal: str = "",
    education: str = "",
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """
    Return top ranked career roles using weighted explainable scoring.
    """
    if not user_skills:
        raise ValueError("User skills list is empty. Please enter at least one skill.")

    result = rank_roles(
        user_skills=user_skills,
        interests=interests,
        user_education=education,
        career_goal=career_goal,
        roles=roles,
        top_n=top_n,
    )
    return result["recommended_roles"]


class CareerMentorCrew:
    """
    Compatibility wrapper for the existing workflow.

    The project still exposes a `CareerMentorCrew` entry point, but role
    ranking is now handled by the explainable local scoring engine so the
    output is deterministic, transparent, and available without external
    services.
    """

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
        education: str,
        career_goal: str,
        roles: dict[str, Any],
    ) -> dict[str, Any]:
        return rank_roles(
            user_skills=user_skills,
            interests=interests,
            user_education=education,
            career_goal=career_goal,
            roles=roles,
            top_n=3,
        )
