"""
skill_normalizer.py
-------------------
Centralized skill normalization, alias resolution, hierarchical inference,
and detailed match analysis.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_ALIASES_FILE = Path(__file__).resolve().parent.parent / "data" / "skill_aliases.json"

_FORMAT_MAP = {
    "react js": "react.js",
    "reactjs": "react.js",
    "node js": "node.js",
    "nodejs": "node.js",
    "express js": "express.js",
    "expressjs": "express.js",
    "mongo db": "mongodb",
    "mongo-db": "mongodb",
    "rest api": "rest apis",
    "restful api": "rest apis",
    "restful apis": "rest apis",
}

CONCEPT_MAP: dict[str, list[str]] = {
    "react.js": ["javascript", "frontend development"],
    "next.js": ["javascript", "react.js", "frontend development"],
    "node.js": ["javascript", "backend development"],
    "express.js": ["node.js", "backend development", "api development", "rest apis"],
    "mongodb": ["database systems"],
    "graphql": ["api development"],
    "rest apis": ["api development"],
    "typescript": ["javascript"],
}


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"[^\w\s.+#/-]", " ", lowered)
    lowered = lowered.replace("_", " ")
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return _FORMAT_MAP.get(lowered, lowered)


@lru_cache(maxsize=1)
def load_skill_aliases() -> dict[str, list[str]]:
    if not _ALIASES_FILE.exists():
        return {}
    with open(_ALIASES_FILE, encoding="utf-8") as fh:
        payload = json.load(fh)
    aliases = {}
    for canonical, values in payload.items():
        aliases[_normalize_text(canonical)] = [_normalize_text(value) for value in values]
    return aliases


def canonicalize_skill(skill: str) -> str:
    normalized = _normalize_text(skill)
    aliases = load_skill_aliases()
    for canonical, variants in aliases.items():
        if normalized == canonical or normalized in variants:
            return canonical
    return normalized


def infer_base_skills(skill: str) -> list[str]:
    canonical = canonicalize_skill(skill)
    return [canonicalize_skill(item) for item in CONCEPT_MAP.get(canonical, [])]


def expand_skill_concepts(skill: str) -> set[str]:
    canonical = canonicalize_skill(skill)
    expanded = {canonical}
    for concept in infer_base_skills(canonical):
        expanded.add(concept)
    return expanded


def normalize_skill_list(skills: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for skill in skills:
        canonical = canonicalize_skill(skill)
        if canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)
        for concept in infer_base_skills(canonical):
            if concept not in seen:
                normalized.append(concept)
                seen.add(concept)
    return normalized


def format_skill_label(skill: str) -> str:
    special = {
        "aws": "AWS",
        "gcp": "GCP",
        "sql": "SQL",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "html": "HTML",
        "css": "CSS",
        "ci/cd": "CI/CD",
        "graphql": "GraphQL",
        "mongodb": "MongoDB",
        "react.js": "React.js",
        "next.js": "Next.js",
        "node.js": "Node.js",
        "express.js": "Express.js",
        "rest apis": "REST APIs",
        "api development": "API Development",
        "database systems": "Database Systems",
        "frontend development": "Frontend Development",
        "backend development": "Backend Development",
    }
    canonical = canonicalize_skill(skill)
    return special.get(canonical, " ".join(part.capitalize() for part in canonical.split()))


def skills_overlap_score(user_skills: list[str], role_skills: list[str]) -> tuple[float, list[str], list[str]]:
    user_concepts = set(normalize_skill_list(user_skills))
    matched = []
    missing = []
    for role_skill in role_skills:
        if user_concepts & expand_skill_concepts(role_skill):
            matched.append(role_skill)
        else:
            missing.append(role_skill)
    score = len(matched) / len(role_skills) if role_skills else 0.0
    return score, matched, missing


def analyze_skill_relationships(
    user_skills: list[str],
    role_skills: list[str],
    *,
    semantic_threshold: float = 0.6,
) -> dict[str, Any]:
    try:
        from backend.semantic_engine import semantic_similarity
    except ImportError:
        from semantic_engine import semantic_similarity

    raw_user = [skill for skill in user_skills if skill.strip()]
    normalized_user = [canonicalize_skill(skill) for skill in raw_user]
    canonical_user_set = set(normalized_user)
    user_concepts = set(normalize_skill_list(raw_user))
    inferred_user_set = user_concepts - canonical_user_set

    direct_matches: list[str] = []
    alias_matches: list[str] = []
    inferred_matches: list[str] = []
    semantic_matches: list[str] = []
    missing_skills: list[str] = []

    for role_skill in role_skills:
        canonical_role = canonicalize_skill(role_skill)
        normalized_role_concepts = expand_skill_concepts(role_skill)

        raw_equal = any(_normalize_text(skill) == _normalize_text(role_skill) for skill in raw_user)
        canonical_equal = canonical_role in normalized_user
        inferred_equal = canonical_role in inferred_user_set or bool(inferred_user_set & normalized_role_concepts)

        semantic_hit = False
        if not raw_equal and not canonical_equal and not inferred_equal:
            best_similarity = 0.0
            for user_skill in raw_user:
                for concept in normalized_role_concepts:
                    best_similarity = max(best_similarity, semantic_similarity(user_skill, concept))
            semantic_hit = best_similarity >= semantic_threshold

        if raw_equal:
            direct_matches.append(role_skill)
        elif canonical_equal:
            alias_matches.append(role_skill)
        elif inferred_equal:
            inferred_matches.append(role_skill)
        elif semantic_hit:
            semantic_matches.append(role_skill)
        else:
            missing_skills.append(role_skill)

    matched_total = len(direct_matches) + len(alias_matches) + len(inferred_matches) + len(semantic_matches)
    return {
        "normalized_user_skills": [format_skill_label(skill) for skill in normalized_user],
        "inferred_user_skills": [format_skill_label(skill) for skill in user_concepts if skill not in normalized_user],
        "direct_matches": direct_matches,
        "alias_matches": alias_matches,
        "inferred_matches": inferred_matches,
        "semantic_matches": semantic_matches,
        "matched_skills": direct_matches + alias_matches + inferred_matches + semantic_matches,
        "missing_skills": missing_skills,
        "overlap_score": matched_total / len(role_skills) if role_skills else 0.0,
    }
