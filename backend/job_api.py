"""
job_api.py
----------
Live job retrieval, NLP-style skill extraction, clustering, caching, and
dynamic role-catalog construction.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

try:
    from backend.semantic_engine import encode_text, semantic_similarity
    from backend.skill_normalizer import canonicalize_skill, format_skill_label, normalize_skill_list
except ImportError:
    from semantic_engine import encode_text, semantic_similarity
    from skill_normalizer import canonicalize_skill, format_skill_label, normalize_skill_list


logger = logging.getLogger(__name__)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _ROOT / ".env"
_DATA_DIR = _ROOT / "data"
_DYNAMIC_ROLES_PATH = _DATA_DIR / "dynamic_roles.json"
_CACHE_PATH = _DATA_DIR / "live_jobs_cache.json"
_DEFAULT_REFRESH_SECONDS = 60 * 60 * 6

SKILL_VOCAB = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "swift", "kotlin", "ruby", "php", "scala", "r", "sql", "nosql",
    "mongodb", "postgresql", "mysql", "redis", "kafka", "spark", "hadoop",
    "tensorflow", "pytorch", "scikit-learn", "machine learning", "deep learning",
    "data science", "data engineering", "power bi", "tableau", "excel",
    "react", "reactjs", "react.js", "react js", "angular", "vue",
    "node", "nodejs", "node.js", "node js", "django", "flask", "fastapi",
    "spring", "express", "expressjs", "express.js", "express js",
    "next.js", "next js", "html", "css", "android", "ios", "flutter",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd", "git",
    "linux", "bash", "cybersecurity", "networking", "figma", "sketch",
    "photoshop", "illustrator", "blender", "after effects", "premiere pro",
    "premiere", "unity", "unreal engine", "unreal", "vfx", "animation", "graphql",
    "rest api", "rest apis", "mongo db", "database systems", "frontend development",
    "backend development", "api development", "data visualization",
    "motion graphics", "video editing", "sound design", "storytelling",
    "communication", "leadership", "project management", "agile", "scrum",
    "jira", "salesforce", "crm", "product management", "business analysis",
]

_SKILL_PATTERNS = [
    (skill, re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE))
    for skill in SKILL_VOCAB
]

ROLE_NORMALISER = {
    "software engineer": "Software Engineer",
    "software developer": "Software Developer",
    "backend developer": "Backend Developer",
    "backend engineer": "Backend Developer",
    "frontend developer": "Frontend Developer",
    "frontend engineer": "Frontend Developer",
    "front end developer": "Frontend Developer",
    "full stack developer": "Full Stack Developer",
    "fullstack developer": "Full Stack Developer",
    "mern stack developer": "MERN Stack Developer",
    "mern developer": "MERN Stack Developer",
    "data scientist": "Data Scientist",
    "data analyst": "Data Analyst",
    "data engineer": "Data Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "ml engineer": "Machine Learning Engineer",
    "devops engineer": "DevOps Engineer",
    "cloud engineer": "Cloud Engineer",
    "cybersecurity analyst": "Cybersecurity Analyst",
    "security engineer": "Security Engineer",
    "product manager": "Product Manager",
    "business analyst": "Business Analyst",
    "project manager": "Project Manager",
    "graphic designer": "Graphic Designer",
    "ux designer": "UX Designer",
    "ui designer": "UI Designer",
    "ui/ux designer": "UI/UX Designer",
    "video editor": "Video Editor",
    "vfx artist": "VFX Artist",
    "motion designer": "Motion Designer",
    "3d animator": "3D Animator",
    "game developer": "Game Developer",
}

ROLE_DOMAIN_MAP = {
    "Software Developer": "Technology",
    "Backend Developer": "Technology",
    "Frontend Developer": "Technology",
    "Full Stack Developer": "Technology",
    "MERN Stack Developer": "Technology",
    "Data Scientist": "Technology",
    "Data Analyst": "Technology",
    "Data Engineer": "Technology",
    "Machine Learning Engineer": "Technology",
    "DevOps Engineer": "Technology",
    "Cloud Engineer": "Technology",
    "Cybersecurity Analyst": "Technology",
    "Security Engineer": "Technology",
    "Product Manager": "Business",
    "Business Analyst": "Business",
    "Project Manager": "Business",
    "Graphic Designer": "Creative",
    "UX Designer": "Creative",
    "UI Designer": "Creative",
    "UI/UX Designer": "Creative",
    "Video Editor": "Media",
    "VFX Artist": "Media",
    "Motion Designer": "Media",
    "3D Animator": "Creative",
    "Game Developer": "Technology",
}

_CLUSTER_HINTS = {
    "Frontend Frameworks": {"react.js", "next.js", "angular", "vue", "frontend development", "html", "css", "javascript", "typescript"},
    "Backend Services": {"node.js", "express.js", "backend development", "api development", "rest apis", "graphql", "python", "java", "go"},
    "Database Systems": {"database systems", "mongodb", "sql", "mysql", "postgresql", "nosql", "redis"},
    "ML and Data": {"machine learning", "deep learning", "data science", "data engineering", "tensorflow", "pytorch", "scikit-learn", "power bi", "tableau", "data visualization"},
    "Cloud and DevOps": {"aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd", "linux", "bash"},
}


def _normalize(text: str) -> str:
    return canonicalize_skill(text)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9+#./-]+", canonicalize_skill(text)) if token}


def _load_runtime_env() -> None:
    if load_dotenv is not None and _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=False)


def _load_cache() -> dict[str, Any]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        with open(_CACHE_PATH, encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_cache(payload: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _cache_key(source: str, query: str, limit: int) -> str:
    return f"{source}:{canonicalize_skill(query)}:{limit}"


def _cache_ttl_seconds() -> int:
    try:
        return int(os.environ.get("LIVE_JOB_REFRESH_SECONDS", str(_DEFAULT_REFRESH_SECONDS)))
    except ValueError:
        return _DEFAULT_REFRESH_SECONDS


def _get_cached_jobs(source: str, query: str, limit: int) -> list[dict[str, Any]] | None:
    cache = _load_cache()
    entry = cache.get(_cache_key(source, query, limit))
    if not isinstance(entry, dict):
        return None
    timestamp = float(entry.get("timestamp", 0))
    age = time.time() - timestamp
    if age > _cache_ttl_seconds():
        return None
    jobs = entry.get("jobs", [])
    return jobs if isinstance(jobs, list) else None


def _set_cached_jobs(source: str, query: str, limit: int, jobs: list[dict[str, Any]]) -> None:
    cache = _load_cache()
    cache[_cache_key(source, query, limit)] = {
        "timestamp": time.time(),
        "jobs": jobs,
    }
    _save_cache(cache)


def _get_stale_jobs(source: str, query: str, limit: int) -> list[dict[str, Any]]:
    cache = _load_cache()
    entry = cache.get(_cache_key(source, query, limit), {})
    jobs = entry.get("jobs", []) if isinstance(entry, dict) else []
    return jobs if isinstance(jobs, list) else []


def _get_adzuna_credentials() -> tuple[str, str, str] | None:
    _load_runtime_env()
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip() or os.environ.get("ADZUNA_API_KEY", "").strip()
    country = os.environ.get("ADZUNA_COUNTRY", "in").strip() or "in"
    if not app_id or not app_key:
        logger.warning(
            "Adzuna credentials missing at runtime. ADZUNA_APP_ID present=%s, ADZUNA_APP_KEY present=%s, env_file=%s",
            bool(app_id),
            bool(app_key),
            str(_ENV_PATH),
        )
        return None
    return app_id, app_key, country


def _title_case_skill(skill: str) -> str:
    return format_skill_label(skill)


def _extract_skills_from_text(text: str) -> list[str]:
    found = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.append(_title_case_skill(skill))
    return list(dict.fromkeys(found))


def _candidate_skill_phrases(text: str) -> list[str]:
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    if not lowered:
        return []

    candidates = []
    for phrase in re.findall(
        r"(?:experience with|required skills?:|must have:|proficient in|knowledge of|familiar with|strong in)\s+([a-z0-9,+#./\-\s]{3,140})",
        lowered,
    ):
        for part in re.split(r",|/| and ", phrase):
            cleaned = part.strip(" .:-")
            if 2 <= len(cleaned) <= 50:
                candidates.append(cleaned)

    tokens = re.findall(r"[a-z0-9+#./-]+", lowered)
    for size in (1, 2, 3):
        for index in range(len(tokens) - size + 1):
            phrase = " ".join(tokens[index:index + size]).strip()
            if 2 <= len(phrase) <= 50:
                candidates.append(phrase)

    ordered = []
    seen = set()
    for candidate in candidates:
        key = candidate.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def extract_required_skills(text: str) -> list[str]:
    direct_matches = _extract_skills_from_text(text)
    if not text.strip():
        return direct_matches

    candidates = _candidate_skill_phrases(text)
    enriched = list(direct_matches)
    enriched_keys = {_normalize(skill) for skill in enriched}

    for vocab_skill in SKILL_VOCAB:
        canonical = _title_case_skill(vocab_skill)
        canonical_key = _normalize(canonical)
        if canonical_key in enriched_keys:
            continue
        best_similarity = 0.0
        for candidate in candidates:
            similarity = semantic_similarity(candidate, vocab_skill)
            if similarity > best_similarity:
                best_similarity = similarity
        if best_similarity >= 0.72:
            enriched.append(canonical)
            enriched_keys.add(canonical_key)

    return [_title_case_skill(skill) for skill in normalize_skill_list(enriched)]


def _infer_domain(text: str) -> str:
    normalized = _normalize(text)
    for label, domain in ROLE_DOMAIN_MAP.items():
        if _normalize(label) in normalized:
            return domain
    keyword_map = {
        "python": "Technology",
        "software": "Technology",
        "developer": "Technology",
        "engineer": "Technology",
        "data": "Technology",
        "security": "Technology",
        "design": "Creative",
        "designer": "Creative",
        "animation": "Creative",
        "video": "Media",
        "vfx": "Media",
        "marketing": "Business",
        "analyst": "Business",
        "product": "Business",
        "project": "Business",
    }
    for keyword, domain in keyword_map.items():
        if keyword in normalized:
            return domain
    return "Dynamic Market"


def _canonicalize_role_name(raw_title: str) -> str:
    lowered = (raw_title or "").strip().lower()
    for alias, canonical in ROLE_NORMALISER.items():
        if alias in lowered:
            return canonical
    cleaned = re.sub(r"\([^)]*\)", "", raw_title or "")
    cleaned = re.sub(r"[-|].*$", "", cleaned).strip()
    return cleaned or "Dynamic Market Role"


def _job_listing(
    *,
    role: str,
    description: str,
    source: str,
    company: str = "",
    location: str = "",
    job_url: str = "",
) -> dict[str, Any]:
    canonical_role = _canonicalize_role_name(role)
    full_text = f"{role}\n{description}"
    skills = extract_required_skills(full_text)
    return {
        "role": canonical_role,
        "raw_role": role,
        "description": (description or "")[:1200],
        "skills": skills,
        "required_skills": skills,
        "domain": ROLE_DOMAIN_MAP.get(canonical_role, _infer_domain(full_text)),
        "source": source,
        "company": company or "Unknown company",
        "location": location or "Unknown location",
        "job_url": job_url,
    }


def _cluster_name(skills: list[str]) -> str:
    normalized = {_normalize(skill) for skill in skills}
    best_name = "Emerging Skills"
    best_overlap = 0
    for cluster_name, hints in _CLUSTER_HINTS.items():
        overlap = len(normalized & hints)
        if overlap > best_overlap:
            best_overlap = overlap
            best_name = cluster_name
    return best_name


def _cluster_skills(skills: list[str]) -> list[dict[str, Any]]:
    unique_skills = []
    seen = set()
    for skill in skills:
        canonical = _normalize(skill)
        if canonical and canonical not in seen:
            unique_skills.append(canonical)
            seen.add(canonical)

    if len(unique_skills) < 2:
        return [{"cluster": _cluster_name(unique_skills), "skills": [_title_case_skill(skill) for skill in unique_skills]}] if unique_skills else []

    embeddings = []
    usable_skills = []
    for skill in unique_skills:
        embedding = encode_text(skill)
        if embedding is not None:
            embeddings.append(embedding)
            usable_skills.append(skill)

    cluster_map: dict[int, list[str]] = defaultdict(list)
    if len(usable_skills) >= 2:
        try:
            from sklearn.cluster import AgglomerativeClustering

            n_clusters = min(max(2, int(math.sqrt(len(usable_skills)))), 6)
            labels = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(embeddings)
            for label, skill in zip(labels, usable_skills):
                cluster_map[int(label)].append(skill)
        except Exception:
            pass

    if not cluster_map:
        heuristic_groups: dict[str, list[str]] = defaultdict(list)
        for skill in unique_skills:
            heuristic_groups[_cluster_name([skill])].append(skill)
        return [
            {"cluster": cluster_name, "skills": [_title_case_skill(skill) for skill in sorted(cluster_skills)]}
            for cluster_name, cluster_skills in heuristic_groups.items()
        ]

    return [
        {
            "cluster": _cluster_name(cluster_skills),
            "skills": [_title_case_skill(skill) for skill in sorted(cluster_skills)],
        }
        for _, cluster_skills in sorted(cluster_map.items(), key=lambda item: (len(item[1]) * -1, item[0]))
    ]


def _persist_dynamic_roles(query: str, jobs: list[dict[str, Any]], roles: dict[str, Any], skill_clusters: list[dict[str, Any]]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "source": "live_job_market",
            "query": query,
            "job_count": len(jobs),
            "role_count": len(roles),
            "updated_at": int(time.time()),
            "refresh_seconds": _cache_ttl_seconds(),
        },
        "roles": list(roles.values()),
        "skill_clusters": skill_clusters,
    }
    with open(_DYNAMIC_ROLES_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def fetch_adzuna_jobs(query: str, limit: int = 5) -> list[dict[str, Any]]:
    cached = _get_cached_jobs("adzuna", query, limit)
    if cached is not None:
        return cached
    if requests is None:
        logger.warning("requests is not installed; Adzuna fetching is unavailable.")
        return _get_stale_jobs("adzuna", query, limit)

    credentials = _get_adzuna_credentials()
    if credentials is None:
        return _get_stale_jobs("adzuna", query, limit)
    app_id, app_key, country = credentials

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": query,
        "content-type": "application/json",
    }

    try:
        logger.info("Requesting Adzuna jobs. query=%r limit=%s country=%s", query, limit, country)
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.warning("Adzuna fetch failed. query=%r error=%s", query, exc)
        return _get_stale_jobs("adzuna", query, limit)

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
    _set_cached_jobs("adzuna", query, limit, jobs)
    return jobs


def fetch_rapidapi_jobs(query: str, limit: int = 5) -> list[dict[str, Any]]:
    cached = _get_cached_jobs("rapidapi", query, limit)
    if cached is not None:
        return cached
    if requests is None:
        return _get_stale_jobs("rapidapi", query, limit)

    api_key = os.environ.get("RAPIDAPI_KEY", "").strip()
    api_host = os.environ.get("RAPIDAPI_JOBS_HOST", "").strip()
    if not api_key or not api_host:
        return _get_stale_jobs("rapidapi", query, limit)

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
    except Exception as exc:
        logger.warning("RapidAPI fetch failed. query=%r host=%s error=%s", query, api_host, exc)
        return _get_stale_jobs("rapidapi", query, limit)

    jobs = []
    items = payload.get("data", []) if isinstance(payload, dict) else []
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
    _set_cached_jobs("rapidapi", query, limit, jobs)
    return jobs


def fetch_live_jobs(query: str, limit_per_source: int = 8) -> list[dict[str, Any]]:
    seen = set()
    jobs = []
    for job in fetch_adzuna_jobs(query, limit_per_source) + fetch_rapidapi_jobs(query, limit_per_source):
        dedupe_key = (
            canonicalize_skill(job.get("role", "")),
            canonicalize_skill(job.get("company", "")),
            canonicalize_skill(job.get("location", "")),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        jobs.append(job)
    return jobs


def fetch_live_jobs_for_roles(role_names: list[str], per_role_limit: int = 3) -> list[dict[str, Any]]:
    seen = set()
    jobs = []
    for role_name in role_names:
        for job in fetch_live_jobs(role_name, per_role_limit):
            dedupe_key = (
                canonicalize_skill(job.get("role", "")),
                canonicalize_skill(job.get("company", "")),
                canonicalize_skill(job.get("location", "")),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            jobs.append(job)
    return jobs


def jobs_to_role_catalog(jobs: list[dict[str, Any]], min_jobs_per_role: int = 1) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "skills": Counter(),
            "descriptions": [],
            "companies": set(),
            "locations": set(),
            "job_count": 0,
            "sources": set(),
            "domain": "Dynamic Market",
            "dynamic_skill_source": "live_jobs",
        }
    )

    for job in jobs:
        role_name = (job.get("role") or "").strip()
        if not role_name:
            continue
        bucket = grouped[role_name]
        bucket["job_count"] += 1
        for skill in job.get("required_skills", []) or job.get("skills", []):
            bucket["skills"][skill] += 1
        description = (job.get("description") or "").strip()
        if description:
            bucket["descriptions"].append(description)
        company = (job.get("company") or "").strip()
        location = (job.get("location") or "").strip()
        if company:
            bucket["companies"].add(company)
        if location:
            bucket["locations"].add(location)
        source = (job.get("source") or "").strip()
        if source:
            bucket["sources"].add(source)
        bucket["domain"] = job.get("domain") or bucket["domain"]

    roles = {}
    for role_name, bucket in grouped.items():
        if bucket["job_count"] < min_jobs_per_role or not bucket["skills"]:
            continue

        total_skill_mentions = sum(bucket["skills"].values()) or 1
        sorted_skills = [skill for skill, _ in bucket["skills"].most_common()]
        skill_weights = {
            skill: round(count / total_skill_mentions, 4)
            for skill, count in bucket["skills"].most_common()
        }
        learned_skills = sorted_skills[:12]
        clusters = _cluster_skills(learned_skills)

        description_bits = []
        if bucket["descriptions"]:
            description_bits.append(bucket["descriptions"][0][:280])
        if bucket["companies"]:
            description_bits.append(f"Hiring signals from {', '.join(sorted(bucket['companies'])[:3])}.")
        description_bits.append(f"Frequently requested skills: {', '.join(learned_skills[:8])}.")

        roles[role_name] = {
            "role": role_name,
            "skills": learned_skills,
            "required_skills": learned_skills,
            "dynamic_learned_skills": learned_skills,
            "static_dataset_skills": [],
            "skill_weights": skill_weights,
            "domain": bucket["domain"],
            "description": " ".join(description_bits).strip(),
            "role_text": f"{role_name}. Skills: {', '.join(learned_skills[:12])}. {' '.join(bucket['descriptions'][:2])[:500]}".strip(),
            "roadmap": learned_skills[:6],
            "degree_required": False,
            "portfolio_required": False,
            "required_degree": [],
            "education_level": "",
            "job_count": bucket["job_count"],
            "hiring_companies": sorted(bucket["companies"])[:5],
            "hiring_locations": sorted(bucket["locations"])[:5],
            "sources": sorted(bucket["sources"]),
            "source": "live_job_market",
            "skill_clusters": clusters,
            "live_job_confidence_contribution": round(min(bucket["job_count"] / 8.0, 1.0) * 100, 1),
        }
    return roles


def build_live_role_catalog(
    user_skills: list[str],
    interests: str = "",
    career_goal: str = "",
    limit_per_source: int = 8,
) -> dict[str, Any]:
    search_terms = []
    if career_goal.strip():
        search_terms.append(career_goal.strip())
    if interests.strip():
        search_terms.append(interests.strip())
    search_terms.extend(user_skills[:5])
    if not search_terms:
        search_terms.append("software developer")

    query = " ".join(search_terms)
    jobs = fetch_live_jobs(query, limit_per_source=limit_per_source)
    role_catalog = jobs_to_role_catalog(jobs)
    global_clusters = _cluster_skills([skill for role in role_catalog.values() for skill in role.get("dynamic_learned_skills", [])])
    _persist_dynamic_roles(query, jobs, role_catalog, global_clusters)

    logger.info(
        "Built live role catalog. query=%r jobs=%s roles=%s",
        query,
        len(jobs),
        len(role_catalog),
    )
    return {
        "query": query,
        "jobs": jobs,
        "roles": role_catalog,
        "skill_clusters": global_clusters,
        "updated_at": int(time.time()),
    }
