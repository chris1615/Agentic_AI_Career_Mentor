"""
domain_engine.py
----------------
Detects the user's primary domain from their skills and interests,
and exposes a lightweight penalty function for cross-domain roles.
"""

from __future__ import annotations

import re
from typing import Sequence

# ---------------------------------------------------------------------------
# Domain → canonical skill keywords
# ---------------------------------------------------------------------------
DOMAIN_SKILL_MAP: dict[str, list[str]] = {
    "Technology": [
        "python", "java", "javascript", "typescript", "react", "node", "nodejs",
        "angular", "vue", "django", "flask", "fastapi", "spring", "express",
        "mongodb", "postgresql", "mysql", "sqlite", "redis", "kafka",
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ci/cd",
        "git", "linux", "bash", "rest", "graphql", "machine learning",
        "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp",
        "data science", "data engineering", "spark", "hadoop", "sql",
        "c++", "c#", "rust", "go", "golang", "swift", "kotlin", "flutter",
        "android", "ios", "devops", "sre", "cybersecurity", "blockchain",
        "solidity", "arduino", "embedded", "raspberry pi",
    ],
    "Creative": [
        "blender", "animation", "3d modeling", "vfx", "visual effects",
        "video editing", "premiere", "after effects", "photoshop", "illustrator",
        "figma", "sketch", "ui design", "ux design", "graphic design",
        "motion graphics", "cinema 4d", "maya", "zbrush", "unity", "unreal",
        "game design", "illustration", "photography", "lightroom", "procreate",
        "typography", "branding", "art direction", "storyboarding",
    ],
    "Business": [
        "excel", "finance", "accounting", "financial modeling", "valuation",
        "analytics", "business analysis", "product management", "agile", "scrum",
        "crm", "salesforce", "marketing", "seo", "sem", "content strategy",
        "supply chain", "operations", "logistics", "hr", "recruitment",
        "consulting", "strategy", "powerpoint", "tableau", "power bi",
        "project management", "pmp", "six sigma",
    ],
    "Healthcare": [
        "nursing", "medicine", "pharmacy", "clinical", "ehr", "emr",
        "patient care", "radiology", "laboratory", "biochemistry", "anatomy",
        "physiology", "pharmacology", "public health", "epidemiology",
        "medical coding", "health informatics",
    ],
    "Education": [
        "teaching", "curriculum", "pedagogy", "e-learning", "instructional design",
        "lms", "moodle", "canvas", "classroom management", "tutoring",
        "training", "learning development",
    ],
}

# Pre-build a flat reverse lookup  { keyword: domain }
_KEYWORD_TO_DOMAIN: dict[str, str] = {
    kw: domain
    for domain, keywords in DOMAIN_SKILL_MAP.items()
    for kw in keywords
}


def _tokenize(text: str) -> list[str]:
    """Lower-case and split on non-alphanumeric chars."""
    return re.findall(r"[a-z0-9#+./-]+", text.lower())


def detect_domain(
    skills: Sequence[str],
    interests: Sequence[str] | None = None,
) -> str:
    """
    Return the most likely domain for the given skills / interests.

    Parameters
    ----------
    skills:    list of skill strings supplied by the user
    interests: optional list of interest/goal strings

    Returns
    -------
    domain string, e.g. ``"Technology"``; falls back to ``"General"``
    """
    all_text = " ".join(list(skills) + list(interests or []))
    tokens = _tokenize(all_text)

    # Score by counting keyword hits per domain
    scores: dict[str, int] = {d: 0 for d in DOMAIN_SKILL_MAP}

    # Single-token scan
    for token in tokens:
        domain = _KEYWORD_TO_DOMAIN.get(token)
        if domain:
            scores[domain] += 1

    # Multi-word keyword scan (up to 3 words)
    for length in (2, 3):
        for i in range(len(tokens) - length + 1):
            phrase = " ".join(tokens[i : i + length])
            domain = _KEYWORD_TO_DOMAIN.get(phrase)
            if domain:
                scores[domain] += length  # weight longer matches more

    best_domain = max(scores, key=lambda d: scores[d])
    if scores[best_domain] == 0:
        return "General"
    return best_domain


def get_domain_penalty(role_domain: str, user_domain: str) -> float:
    """
    Return a score multiplier for a role given the user's detected domain.

    * Same domain (or either side is ``"General"``) → ``1.0``  (no penalty)
    * Cross-domain mismatch                          → ``0.6``  (40 % penalty)
    """
    if user_domain == "General" or role_domain == "General":
        return 1.0
    if role_domain.lower() == user_domain.lower():
        return 1.0
    return 0.6
