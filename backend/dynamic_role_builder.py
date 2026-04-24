"""
dynamic_role_builder.py
-----------------------
Fetches live job descriptions from the Adzuna API, extracts key skills,
groups them by role title, and writes the result to data/dynamic_roles.json.

Usage
-----
    # from Python
    from backend.dynamic_role_builder import refresh_dynamic_roles
    refresh_dynamic_roles()

    # from CLI
    python -m backend.dynamic_role_builder

Environment variables (set in .env)
-------------------------------------
    ADZUNA_APP_ID  – your Adzuna application id
    ADZUNA_API_KEY – your Adzuna API key
    ADZUNA_COUNTRY – two-letter country code, default "gb"
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_DATA_DIR = _HERE.parent / "data"
_OUTPUT_FILE = _DATA_DIR / "dynamic_roles.json"

# ---------------------------------------------------------------------------
# Skill keyword vocabulary used for extraction
# ---------------------------------------------------------------------------
_SKILL_VOCAB: list[str] = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "swift", "kotlin", "ruby", "php", "scala", "r",
    # Web / mobile
    "react", "angular", "vue", "node", "nodejs", "django", "flask", "fastapi",
    "spring", "express", "next.js", "flutter", "android", "ios",
    # Data / ML
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis", "kafka",
    "spark", "hadoop", "tensorflow", "pytorch", "scikit-learn",
    "machine learning", "deep learning", "nlp", "data science",
    "data engineering", "power bi", "tableau",
    # Cloud / DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
    "git", "linux", "bash",
    # Design / Creative
    "figma", "sketch", "photoshop", "illustrator", "blender", "after effects",
    "premiere", "unity", "unreal",
    # Business
    "excel", "salesforce", "sap", "crm", "agile", "scrum", "jira",
    "project management",
]

# Pre-compile patterns for speed
_SKILL_PATTERNS = [
    (skill, re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE))
    for skill in _SKILL_VOCAB
]

# Role title → canonical name  (normalise noisy Adzuna titles)
_ROLE_NORMALISER: dict[str, str] = {
    "software engineer": "Software Engineer",
    "software developer": "Software Engineer",
    "backend developer": "Backend Developer",
    "frontend developer": "Frontend Developer",
    "full stack developer": "Full Stack Developer",
    "fullstack developer": "Full Stack Developer",
    "data scientist": "Data Scientist",
    "data engineer": "Data Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "ml engineer": "Machine Learning Engineer",
    "devops engineer": "DevOps Engineer",
    "cloud engineer": "Cloud Engineer",
    "product manager": "Product Manager",
    "ux designer": "UX Designer",
    "ui designer": "UI Designer",
    "ui/ux designer": "UI/UX Designer",
    "graphic designer": "Graphic Designer",
    "3d artist": "3D Artist",
    "3d animator": "3D Animator",
    "motion designer": "Motion Designer",
    "financial analyst": "Financial Analyst",
    "business analyst": "Business Analyst",
    "data analyst": "Data Analyst",
    "project manager": "Project Manager",
    "cybersecurity analyst": "Cybersecurity Analyst",
    "security engineer": "Security Engineer",
}

# Domain lookup for canonical role names
_ROLE_DOMAIN_MAP: dict[str, str] = {
    "Software Engineer": "Technology",
    "Backend Developer": "Technology",
    "Frontend Developer": "Technology",
    "Full Stack Developer": "Technology",
    "Data Scientist": "Technology",
    "Data Engineer": "Technology",
    "Machine Learning Engineer": "Technology",
    "DevOps Engineer": "Technology",
    "Cloud Engineer": "Technology",
    "Data Analyst": "Technology",
    "Cybersecurity Analyst": "Technology",
    "Security Engineer": "Technology",
    "Product Manager": "Business",
    "Business Analyst": "Business",
    "Project Manager": "Business",
    "Financial Analyst": "Business",
    "UX Designer": "Creative",
    "UI Designer": "Creative",
    "UI/UX Designer": "Creative",
    "Graphic Designer": "Creative",
    "3D Artist": "Creative",
    "3D Animator": "Creative",
    "Motion Designer": "Creative",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_skills(text: str) -> list[str]:
    found = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.append(skill)
    return list(dict.fromkeys(found))  # deduplicate, preserve order


def _normalise_title(raw_title: str) -> str | None:
    lower = raw_title.lower().strip()
    for key, canonical in _ROLE_NORMALISER.items():
        if key in lower:
            return canonical
    return None


# ---------------------------------------------------------------------------
# Adzuna fetch
# ---------------------------------------------------------------------------

def _fetch_adzuna_jobs(
    query: str,
    app_id: str,
    api_key: str,
    country: str = "gb",
    results_per_page: int = 20,
) -> list[dict[str, Any]]:
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": api_key,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as exc:
        logger.warning("Adzuna fetch failed for '%s': %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

_SEARCH_QUERIES = [
    "software engineer",
    "data scientist",
    "frontend developer",
    "backend developer",
    "devops engineer",
    "product manager",
    "ux designer",
    "graphic designer",
    "business analyst",
    "machine learning engineer",
    "cybersecurity analyst",
    "data engineer",
    "3d animator",
]


def refresh_dynamic_roles(
    app_id: str | None = None,
    api_key: str | None = None,
    country: str | None = None,
    queries: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch live job listings, extract skills, and persist to
    ``data/dynamic_roles.json``.

    Returns the list of built role dicts (also written to disk).
    """
    app_id  = app_id  or os.getenv("ADZUNA_APP_ID", "")
    api_key = api_key or os.getenv("ADZUNA_API_KEY", "")
    country = country or os.getenv("ADZUNA_COUNTRY", "gb")

    if not app_id or not api_key:
        logger.warning(
            "ADZUNA_APP_ID / ADZUNA_API_KEY not set. "
            "Skipping dynamic role refresh."
        )
        return []

    queries = queries or _SEARCH_QUERIES

    # role_name → {"skills": set, "descriptions": [str], "domain": str}
    aggregated: dict[str, dict] = defaultdict(
        lambda: {"skills": set(), "descriptions": [], "domain": "General"}
    )

    for query in queries:
        jobs = _fetch_adzuna_jobs(query, app_id, api_key, country)
        for job in jobs:
            raw_title   = job.get("title", "")
            description = job.get("description", "")
            canonical   = _normalise_title(raw_title)
            if not canonical:
                continue
            skills = _extract_skills(description + " " + raw_title)
            aggregated[canonical]["skills"].update(skills)
            aggregated[canonical]["descriptions"].append(description[:300])
            aggregated[canonical]["domain"] = _ROLE_DOMAIN_MAP.get(canonical, "General")
        time.sleep(0.3)  # be polite to the API

    # Build output list
    roles: list[dict[str, Any]] = []
    for role_name, data in aggregated.items():
        skill_list = sorted(data["skills"])
        if not skill_list:
            continue
        roles.append({
            "role": role_name,
            "domain": data["domain"],
            "required_skills": skill_list,
            "description": f"Dynamically built from live job listings. "
                           f"Common skills: {', '.join(skill_list[:8])}.",
            "source": "adzuna_dynamic",
        })

    # Persist
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(roles, fh, indent=2)
    logger.info("Saved %d dynamic roles to %s", len(roles), _OUTPUT_FILE)
    return roles


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = refresh_dynamic_roles()
    print(f"Built {len(result)} dynamic roles.")
