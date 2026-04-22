"""
job_api.py
----------
Live job retrieval helpers for recommended careers.
"""

from __future__ import annotations

import os
import re
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None


COMMON_JOB_SKILLS = [
    "Python", "SQL", "Excel", "Blender", "VFX", "Video Editing", "Animation",
    "C++", "C#", "Unity", "Unreal Engine", "Motion Graphics", "Sound Design",
    "Linux", "Cybersecurity", "Machine Learning", "Data Visualization",
    "Communication", "Design", "Storytelling", "Premiere Pro", "After Effects",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _extract_skills_from_text(text: str) -> list[str]:
    lower = text.lower()
    return [skill for skill in COMMON_JOB_SKILLS if skill.lower() in lower]


def _job_listing(
    *,
    role: str,
    description: str,
    source: str,
    company: str = "",
    location: str = "",
    job_url: str = "",
) -> dict[str, Any]:
    return {
        "role": role,
        "description": description[:500],
        "skills": _extract_skills_from_text(f"{role} {description}"),
        "source": source,
        "company": company or "Unknown company",
        "location": location or "Unknown location",
        "job_url": job_url,
    }


def fetch_adzuna_jobs(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if requests is None:
        return []

    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        return []

    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": query,
        "content-type": "application/json",
    }

    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    jobs = []
    for item in payload.get("results", [])[:limit]:
        jobs.append(
            _job_listing(
                role=item.get("title", query),
                description=item.get("description", ""),
                source="Adzuna",
                company=(item.get("company") or {}).get("display_name", ""),
                location=(item.get("location") or {}).get("display_name", ""),
                job_url=item.get("redirect_url", ""),
            )
        )
    return jobs


def fetch_rapidapi_jobs(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if requests is None:
        return []

    api_key = os.environ.get("RAPIDAPI_KEY", "").strip()
    api_host = os.environ.get("RAPIDAPI_JOBS_HOST", "").strip()
    if not api_key or not api_host:
        return []

    url = f"https://{api_host}/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": api_host,
    }
    params = {"query": query, "page": "1", "num_pages": "1"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    items = payload.get("data", []) if isinstance(payload, dict) else []
    jobs = []
    for item in items[:limit]:
        description = item.get("job_description", "") or str(item.get("job_highlights", ""))
        jobs.append(
            _job_listing(
                role=item.get("job_title", query),
                description=description,
                source="RapidAPI",
                company=item.get("employer_name", ""),
                location=item.get("job_city", "") or item.get("job_country", ""),
                job_url=item.get("job_apply_link", ""),
            )
        )
    return jobs


def fetch_live_jobs_for_roles(role_names: list[str], per_role_limit: int = 3) -> list[dict[str, Any]]:
    seen = set()
    jobs = []
    for role_name in role_names:
        for job in fetch_adzuna_jobs(role_name, per_role_limit) + fetch_rapidapi_jobs(role_name, per_role_limit):
            dedupe_key = (_normalize(job.get("role", "")), _normalize(job.get("company", "")), _normalize(job.get("location", "")))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            jobs.append(job)
    return jobs


def jobs_to_role_catalog(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    roles = {}
    for job in jobs:
        role_name = (job.get("role") or "").strip()
        if not role_name or role_name in roles:
            continue
        roles[role_name] = {
            "skills": job.get("skills", []),
            "domain": "Dynamic Market",
            "description": job.get("description", ""),
            "roadmap": job.get("skills", [])[:6],
            "degree_required": False,
            "portfolio_required": False,
            "required_degree": [],
            "education_level": "",
        }
    return roles
