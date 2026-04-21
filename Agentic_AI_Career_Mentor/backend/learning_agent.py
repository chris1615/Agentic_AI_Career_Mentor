"""
learning_agent.py
-----------------
Learning Planner Agent.

Builds role-specific phased roadmaps so each recommended career has its own
separate learning path with no topic mixing across roles.
"""

from __future__ import annotations

from typing import Any


_RESOURCE_HINTS = {
    "python": "Start with Python.org docs, Automate the Boring Stuff, or beginner project tutorials.",
    "sql": "Use SQLZoo, Mode SQL Tutorial, or PostgreSQL tutorials for practice.",
    "machine learning": "Study with Andrew Ng courses, fast.ai, and small model projects.",
    "excel": "Use ExcelJet, Microsoft Learn, and spreadsheet practice tasks.",
    "linux": "Practice in a Linux VM using command-line fundamentals tutorials.",
    "networking": "Study networking basics with Cisco NetAcad or free networking labs.",
    "cybersecurity": "Use TryHackMe, Hack The Box, or intro cyber labs.",
    "statistics": "Use Khan Academy, StatQuest, and applied analysis exercises.",
    "figma": "Use Figma official tutorials and redesign challenges.",
    "seo": "Use Moz's beginner guides and Google Search Central resources.",
}


def _resource_hint_for_topic(topic: str) -> str:
    lower_topic = topic.lower()
    for key, hint in _RESOURCE_HINTS.items():
        if key in lower_topic:
            return hint
    return f"Search for a beginner-friendly course or guided project on {topic}."


def _phase_title(index: int) -> str:
    return ["Phase 1 - Foundation", "Phase 2 - Core Skills", "Phase 3 - Advanced Skills"][index]


def _chunk_topics(topics: list[str]) -> list[list[str]]:
    if not topics:
        return [[], [], []]

    total = len(topics)
    foundation_end = max(1, total // 3)
    core_end = max(foundation_end + 1, (2 * total) // 3)

    return [
        topics[:foundation_end],
        topics[foundation_end:core_end],
        topics[core_end:],
    ]


def _build_phase_steps(topics: list[str], missing_skills: list[str]) -> list[str]:
    steps = []
    normalized_missing = {skill.strip().lower() for skill in missing_skills}

    for topic in topics:
        if topic.strip().lower() in normalized_missing:
            steps.append(f"Prioritize {topic} because it is currently missing for this role.")
        else:
            steps.append(f"Strengthen {topic} to improve readiness for the role.")

    return steps


def generate_role_learning_plan(role_name: str, role_data: dict[str, Any], missing_skills: list[str]) -> list[dict[str, Any]]:
    """
    Build a phased roadmap for a single role using that role's own roadmap field
    and missing skills only.
    """
    roadmap = role_data.get("roadmap", []) or []
    phases_source = _chunk_topics(roadmap)
    phase_plans = []

    for index, topics in enumerate(phases_source):
        if not topics:
            continue

        phase_plans.append(
            {
                "phase": _phase_title(index),
                "topics": topics,
                "steps": _build_phase_steps(topics, missing_skills),
                "resource_hint": _resource_hint_for_topic(topics[0]),
            }
        )

    if not phase_plans and missing_skills:
        fallback_topics = missing_skills[:]
        phase_plans = [
            {
                "phase": "Phase 1 - Foundation",
                "topics": fallback_topics,
                "steps": _build_phase_steps(fallback_topics, missing_skills),
                "resource_hint": _resource_hint_for_topic(fallback_topics[0]),
            }
        ]

    return phase_plans


def generate_learning_plan(missing_skills: list[str], role_name: str = "", role_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Backward-compatible wrapper.

    When role data is provided, it generates a role-specific phased roadmap.
    Otherwise it falls back to a simple single-role-compatible sequence.
    """
    if not missing_skills and not role_data:
        return []

    if role_data:
        return generate_role_learning_plan(role_name, role_data, missing_skills)

    return [
        {
            "phase": "Phase 1 - Foundation",
            "topics": missing_skills,
            "steps": [f"Learn {skill} through guided practice and beginner projects." for skill in missing_skills],
            "resource_hint": _resource_hint_for_topic(missing_skills[0]) if missing_skills else "",
        }
    ]
