"""
data_loader.py
--------------
Loads and merges the static roles dataset with the dynamically built one.

Priority
--------
1. ``data/roles_dataset.json``   – hand-curated static dataset
2. ``data/dynamic_roles.json``   – built by dynamic_role_builder.py

Duplicate roles (matched by lower-cased role name) are resolved by keeping
the static entry and *merging* any additional required_skills from the
dynamic entry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR   = Path(__file__).parent.parent / "data"
_STATIC_DB  = _DATA_DIR / "roles_dataset.json"
_CAREER_DB  = _DATA_DIR / "career_dataset.json"
_DYNAMIC_DB = _DATA_DIR / "dynamic_roles.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_role_record(role_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    required_skills = payload.get("required_skills") or payload.get("skills") or []
    return {
        "role": role_name,
        "domain": payload.get("domain", payload.get("category", "General")),
        "description": payload.get("description", ""),
        "required_skills": list(required_skills),
        "skills": list(payload.get("skills") or required_skills),
        "roadmap": list(payload.get("roadmap") or payload.get("career_path_steps") or []),
        "degree_required": bool(payload.get("degree_required", False)),
        "portfolio_required": bool(payload.get("portfolio_required", False)),
        "required_degree": list(payload.get("required_degree") or payload.get("education_required") or []),
        "education_level": payload.get("education_level", ""),
    }


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        logger.debug("Dataset not found, skipping: %s", path)
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if all(isinstance(value, dict) for value in data.values()):
                return [_coerce_role_record(role_name, payload) for role_name, payload in data.items()]
            for key in ("roles", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            if "careers" in data and isinstance(data["careers"], list):
                normalized = []
                for item in data["careers"]:
                    if not isinstance(item, dict):
                        continue
                    normalized.append(
                        {
                            "role": item.get("career_name", "Career Role"),
                            "domain": item.get("domain", item.get("category", "General")),
                            "description": item.get("description", ""),
                            "required_skills": list(item.get("required_skills") or []),
                            "skills": list(item.get("required_skills") or []),
                            "roadmap": list(item.get("career_path_steps") or []),
                            "degree_required": True,
                            "portfolio_required": False,
                            "required_degree": list(item.get("education_required") or []),
                            "education_level": item.get("experience_level", ""),
                        }
                    )
                return normalized
        logger.warning("Unexpected JSON structure in %s", path)
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return []


def _merge(
    static: list[dict[str, Any]],
    dynamic: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge *dynamic* into *static*.

    * Static entries always win on all fields except ``required_skills``.
    * ``required_skills`` from both sources are union-merged.
    * Dynamic-only roles are appended at the end.
    """
    merged: dict[str, dict[str, Any]] = {}

    for role in static:
        key = role.get("role", "").strip().lower()
        if key:
            merged[key] = dict(role)

    for role in dynamic:
        key = role.get("role", "").strip().lower()
        if not key:
            continue
        if key in merged:
            # Merge skills only
            existing_skills = set(merged[key].get("required_skills", []))
            new_skills      = set(role.get("required_skills", []))
            merged[key]["required_skills"] = sorted(existing_skills | new_skills)
            merged[key]["skills"] = sorted(set(merged[key].get("skills", [])) | set(role.get("skills", [])))
            for field in (
                "dynamic_learned_skills",
                "static_dataset_skills",
                "skill_weights",
                "skill_clusters",
                "job_count",
                "live_job_confidence_contribution",
                "sources",
                "role_text",
            ):
                if field in role and role[field]:
                    merged[key][field] = role[field]
        else:
            merged[key] = dict(role)

    return list(merged.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_roles() -> list[dict[str, Any]]:
    """
    Return the combined list of career roles from static + dynamic datasets.

    Always succeeds – returns ``[]`` if no data files exist yet.
    """
    static  = _load_json(_STATIC_DB)
    if not static:
        static = _load_json(_CAREER_DB)
    dynamic = _load_json(_DYNAMIC_DB)

    if not static and not dynamic:
        logger.warning(
            "No role datasets found. "
            "Add data/roles_dataset.json, data/career_dataset.json, or run dynamic_role_builder."
        )
        return []

    roles = _merge(static, dynamic)
    logger.info(
        "Loaded %d roles (%d static, %d dynamic, %d merged unique).",
        len(roles), len(static), len(dynamic), len(roles),
    )
    return roles
