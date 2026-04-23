"""
career_api_provider.py
----------------------
API-first career intelligence powered by O*NET Web Services.

This module provides:
- occupation recommendations based on user skills/interests/goals
- role enrichment with education, outlook, work-style, and technology data
- grounded Q&A over the suggested careers

If the API is unavailable or not configured, callers should fall back to the
local dataset pipeline.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any


ONET_API_BASE = os.environ.get("ONET_API_BASE", "https://api-v2.onetcenter.org")
ONET_API_KEY_ENV = "ONET_API_KEY"
DEFAULT_TIMEOUT = 20


class CareerAPIError(RuntimeError):
    """Raised when the external career API cannot satisfy a request."""


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().replace("/", " ").replace("-", " ").split())


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        key = _normalize(value)
        if not key or key in seen:
            continue
        deduped.append(value)
        seen.add(key)
    return deduped


def _to_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _best_text_matches(term: str, candidates: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    normalized_term = _normalize(term)
    ranked = []
    for candidate in candidates:
        title = _normalize(candidate.get("title") or candidate.get("name") or "")
        if not title:
            continue
        ratio = SequenceMatcher(None, normalized_term, title).ratio()
        if normalized_term == title:
            ratio = 1.0
        elif normalized_term in title or title in normalized_term:
            ratio = max(ratio, 0.82)
        elif set(normalized_term.split()) & set(title.split()):
            ratio = max(ratio, 0.6)

        candidate_copy = dict(candidate)
        candidate_copy["_match_ratio"] = ratio
        ranked.append(candidate_copy)

    ranked.sort(key=lambda item: (-item["_match_ratio"], item.get("title") or item.get("name") or ""))
    return [item for item in ranked if item["_match_ratio"] >= 0.45][:limit]


def _as_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "occupation", "occupations", "careers", "examples", "skills"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _flatten_skill_nodes(payload: Any, source: str) -> list[dict[str, Any]]:
    flattened = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return

        code = node.get("id") or node.get("code") or node.get("element_id")
        title = node.get("title") or node.get("name")
        if code and title:
            flattened.append({"id": code, "title": title, "source": source})

        for key in ("children", "elements", "categories", "subcategories"):
            if key in node:
                walk(node.get(key))

    walk(payload)
    return flattened


@dataclass
class ONetCareerAPI:
    api_key: str
    base_url: str = ONET_API_BASE
    timeout: int = DEFAULT_TIMEOUT

    @classmethod
    def from_env(cls) -> "ONetCareerAPI | None":
        api_key = os.environ.get(ONET_API_KEY_ENV, "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)

    def _request_json(self, path: str, query: dict[str, Any] | None = None) -> Any:
        query = query or {}
        encoded_query = urllib.parse.urlencode(
            {key: value for key, value in query.items() if value not in (None, "")}
        )
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if encoded_query:
            url = f"{url}?{encoded_query}"

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "X-API-Key": self.api_key,
            },
        )

        ssl_context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network path
            raise CareerAPIError(f"O*NET request failed for '{path}': {exc}") from exc

    @lru_cache(maxsize=1)
    def get_skill_catalog(self) -> list[dict[str, Any]]:
        skills = []
        for endpoint, source in (
            ("online/onet_data/skills_basic", "skills_basic"),
            ("online/onet_data/skills_cross_functional", "skills_cross_functional"),
        ):
            payload = self._request_json(endpoint)
            skills.extend(_flatten_skill_nodes(payload, source))
        return _dedupe_skill_catalog(skills)

    def search_occupations(self, keyword: str, end: int = 10) -> list[dict[str, Any]]:
        payload = self._request_json("mnm/search", {"keyword": keyword, "end": end})
        occupations = _as_list(payload)
        results = []
        for item in occupations:
            code = item.get("code") or item.get("onet_soc_code")
            title = item.get("title") or item.get("name")
            if code and title:
                results.append({"code": code, "title": title})
        return results

    def search_technology_examples(self, keyword: str, end: int = 5) -> list[dict[str, Any]]:
        payload = self._request_json("online/technology/examples/search", {"keyword": keyword, "end": end})
        examples = _as_list(payload)
        results = []
        for item in examples:
            title = item.get("example") or item.get("title") or item.get("name")
            if title:
                results.append({"id": title, "title": title})
        return results

    def occupations_for_skill(self, skill_ids: list[str], end: int = 10) -> list[dict[str, Any]]:
        payload = self._request_json("online/soft_skills/results", {"skills": ",".join(skill_ids), "end": end})
        occupations = _as_list(payload)
        results = []
        for item in occupations:
            code = item.get("code") or item.get("onet_soc_code")
            title = item.get("title") or item.get("name")
            if not code or not title:
                continue
            results.append(
                {
                    "code": code,
                    "title": title,
                    "importance": _to_number(item.get("importance")),
                    "level": _to_number(item.get("level")),
                }
            )
        return results

    def occupations_for_technology(self, technology_id: str, end: int = 10) -> list[dict[str, Any]]:
        payload = self._request_json(
            f"online/technology/examples/{urllib.parse.quote(technology_id)}",
            {"end": end},
        )
        occupations = _as_list(payload)
        results = []
        for item in occupations:
            code = item.get("code") or item.get("onet_soc_code")
            title = item.get("title") or item.get("name")
            if code and title:
                results.append({"code": code, "title": title})
        return results

    def get_occupation_summary(self, code: str) -> dict[str, Any]:
        payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}")
        return payload if isinstance(payload, dict) else {}

    def get_occupation_details(self, code: str) -> dict[str, Any]:
        summary = self.get_occupation_summary(code)
        skills_payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}/skills")
        education_payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}/education")
        personality_payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}/personality")
        technology_payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}/technology")
        outlook_payload = self._request_json(f"mnm/careers/{urllib.parse.quote(code)}/outlook")

        return {
            "summary": summary,
            "skills": skills_payload,
            "education": education_payload,
            "personality": personality_payload,
            "technology": technology_payload,
            "outlook": outlook_payload,
        }


def _dedupe_skill_catalog(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    catalog = []
    for item in skills:
        key = (_normalize(item.get("id")), _normalize(item.get("title")))
        if key in seen:
            continue
        catalog.append(item)
        seen.add(key)
    return catalog


def _extract_top_skill_names(details: dict[str, Any], limit: int = 8) -> list[str]:
    skills_payload = details.get("skills") or {}
    candidates = _as_list(skills_payload)
    scored = []
    for item in candidates:
        title = item.get("title") or item.get("name")
        if not title:
            continue
        score = _to_number(item.get("score")) + _to_number(item.get("importance")) + _to_number(item.get("level"))
        scored.append((score, title))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return _dedupe_keep_order([title for _, title in scored[:limit]])


def _extract_technology_examples(details: dict[str, Any], limit: int = 8) -> list[str]:
    technology_payload = details.get("technology") or {}
    examples = _as_list(technology_payload)
    titles = []
    for item in examples:
        title = item.get("example") or item.get("title") or item.get("name")
        if title:
            titles.append(title)
    return _dedupe_keep_order(titles[:limit])


def _extract_work_styles(details: dict[str, Any], limit: int = 6) -> list[str]:
    personality_payload = details.get("personality") or {}
    items = _as_list(personality_payload)
    styles = []
    for item in items:
        title = item.get("title") or item.get("name")
        if title:
            styles.append(title)
    return _dedupe_keep_order(styles[:limit])


def _extract_education_text(details: dict[str, Any]) -> str:
    education_payload = details.get("education") or {}
    fields = [
        education_payload.get("required_level"),
        education_payload.get("most_common_education"),
        education_payload.get("education_needed"),
        education_payload.get("job_zone"),
        education_payload.get("summary"),
    ]
    for field in fields:
        if isinstance(field, str) and field.strip():
            return field.strip()
    return "Education guidance is available from the provider, but this occupation did not return a concise summary."


def _extract_outlook_text(details: dict[str, Any]) -> str:
    summary = details.get("summary") or {}
    outlook_payload = details.get("outlook") or {}
    fields = [
        outlook_payload.get("summary"),
        outlook_payload.get("outlook"),
        summary.get("bright_outlook"),
        summary.get("outlook"),
        summary.get("job_outlook"),
        summary.get("projected_growth"),
    ]
    for field in fields:
        if isinstance(field, str) and field.strip():
            return field.strip()
    return "No concise outlook summary was returned by the provider."


def _extract_salary_text(summary: dict[str, Any]) -> str:
    fields = [
        summary.get("annual_salary"),
        summary.get("wages"),
        summary.get("salary"),
        summary.get("median_wage"),
    ]
    for field in fields:
        if isinstance(field, str) and field.strip():
            return field.strip()
    return "Salary data was not returned for this occupation."


def _build_career_intel(code: str, title: str, details: dict[str, Any], matched_terms: list[str], score: float) -> dict[str, Any]:
    summary = details.get("summary") or {}
    what_they_do = (
        summary.get("what_they_do")
        or summary.get("description")
        or summary.get("what")
        or "No role summary was returned by the provider."
    )
    on_the_job = summary.get("on_the_job") or summary.get("tasks") or []
    if isinstance(on_the_job, str):
        on_the_job = [on_the_job]

    key_skills = _extract_top_skill_names(details)
    technology = _extract_technology_examples(details)
    work_styles = _extract_work_styles(details)

    missing = []
    normalized_matches = {_normalize(term) for term in matched_terms}
    for skill in key_skills + technology:
        if _normalize(skill) not in normalized_matches:
            missing.append(skill)

    return {
        "code": code,
        "role": title,
        "domain": "Career Intelligence",
        "match_score": round(score, 1),
        "matched_skills": _dedupe_keep_order(matched_terms),
        "missing_skills": _dedupe_keep_order(missing)[:8],
        "description": what_they_do,
        "what_they_do": what_they_do,
        "on_the_job": on_the_job[:5],
        "education": _extract_education_text(details),
        "outlook": _extract_outlook_text(details),
        "salary": _extract_salary_text(summary),
        "key_skills": key_skills,
        "technology": technology,
        "work_styles": work_styles,
    }


def recommend_careers_via_api(
    *,
    user_skills: list[str],
    interests: str = "",
    career_goal: str = "",
    top_n: int = 3,
) -> dict[str, Any]:
    """
    Recommend careers using O*NET Web Services.

    Returns the same core `recommended_roles` shape as the dataset path and
    supplements it with `career_intel`.
    """
    api = ONetCareerAPI.from_env()
    if api is None:
        raise CareerAPIError("ONET_API_KEY is not configured.")
    if not user_skills:
        raise CareerAPIError("At least one skill is required for career recommendations.")

    skill_catalog = api.get_skill_catalog()
    aggregate: dict[str, dict[str, Any]] = {}

    def touch_occupation(code: str, title: str) -> dict[str, Any]:
        if code not in aggregate:
            aggregate[code] = {
                "code": code,
                "title": title,
                "score": 0.0,
                "matched_terms": [],
                "evidence": [],
            }
        return aggregate[code]

    for skill in user_skills:
        normalized_skill = _normalize(skill)
        if not normalized_skill:
            continue

        matches = _best_text_matches(skill, skill_catalog, limit=3)
        if matches:
            matched_skill_ids = [matched_skill["id"] for matched_skill in matches]
            for occupation in api.occupations_for_skill(matched_skill_ids, end=8):
                entry = touch_occupation(occupation["code"], occupation["title"])
                contribution = 25 + (occupation["importance"] * 4) + (occupation["level"] * 2)
                entry["score"] += contribution
                entry["matched_terms"].append(skill)
                for matched_skill in matches:
                    entry["evidence"].append(f"skill:{matched_skill['title']}")

        technology_matches = api.search_technology_examples(skill, end=3)
        for technology in technology_matches:
            for occupation in api.occupations_for_technology(technology["id"], end=6):
                entry = touch_occupation(occupation["code"], occupation["title"])
                entry["score"] += 28
                entry["matched_terms"].append(skill)
                entry["evidence"].append(f"technology:{technology['title']}")

        for rank, occupation in enumerate(api.search_occupations(skill, end=5), start=1):
            entry = touch_occupation(occupation["code"], occupation["title"])
            entry["score"] += max(10 - rank, 4)
            entry["matched_terms"].append(skill)
            entry["evidence"].append("keyword_search")

    for text in [interests, career_goal]:
        normalized_text = _normalize(text)
        if not normalized_text:
            continue
        for rank, occupation in enumerate(api.search_occupations(text, end=6), start=1):
            entry = touch_occupation(occupation["code"], occupation["title"])
            entry["score"] += max(8 - rank, 2)
            entry["evidence"].append("intent_search")

    if not aggregate:
        raise CareerAPIError("The career API returned no occupations for the supplied profile.")

    ranked = sorted(
        aggregate.values(),
        key=lambda item: (-item["score"], -len(_dedupe_keep_order(item["matched_terms"])), item["title"]),
    )
    max_score = ranked[0]["score"] or 1.0

    recommended_roles = []
    career_intel = []
    combined_missing = []

    for entry in ranked[:top_n]:
        details = api.get_occupation_details(entry["code"])
        normalized_score = (entry["score"] / max_score) * 100
        intel = _build_career_intel(
            entry["code"],
            entry["title"],
            details,
            _dedupe_keep_order(entry["matched_terms"]),
            normalized_score,
        )
        recommended_roles.append(
            {
                "role": intel["role"],
                "domain": intel["domain"],
                "match_score": intel["match_score"],
                "matched_skills": intel["matched_skills"],
                "missing_skills": intel["missing_skills"],
                "description": intel["description"],
            }
        )
        career_intel.append(intel)
        combined_missing.extend(intel["missing_skills"])

    return {
        "recommended_roles": recommended_roles,
        "career_intel": career_intel,
        "missing_skills": _dedupe_keep_order(combined_missing),
        "provider": "onet",
    }


def answer_career_question(question: str, career_intel: list[dict[str, Any]]) -> str:
    """
    Answer a question grounded in the fetched career-intelligence payload.

    If OPENAI_API_KEY is present, this uses OpenAI for more flexible synthesis.
    Otherwise it falls back to a deterministic summarizer.
    """
    normalized_question = _normalize(question)
    if not normalized_question:
        return "Ask a question about the suggested careers to explore their duties, skills, education, outlook, or salary."
    if not career_intel:
        return "No career intelligence is available yet. Run the analysis first."

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-"):
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            context = json.dumps(career_intel, indent=2, ensure_ascii=True)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.2,
                max_tokens=350,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided career-intelligence JSON. "
                            "If the answer is not present, say that the current provider data does not include it."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Career intelligence:\n{context}\n\nQuestion: {question}",
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    if any(token in normalized_question for token in ("salary", "pay", "wage", "compensation")):
        return "\n".join(f"{item['role']}: {item.get('salary', 'Salary data unavailable.')}" for item in career_intel)
    if any(token in normalized_question for token in ("education", "degree", "qualification", "study")):
        return "\n".join(f"{item['role']}: {item.get('education', 'Education guidance unavailable.')}" for item in career_intel)
    if any(token in normalized_question for token in ("outlook", "growth", "future", "demand")):
        return "\n".join(f"{item['role']}: {item.get('outlook', 'Outlook data unavailable.')}" for item in career_intel)
    if any(token in normalized_question for token in ("skill", "skills", "learn", "tool", "technology")):
        lines = []
        for item in career_intel:
            skills = ", ".join(item.get("key_skills", [])[:6]) or "Not available"
            tech = ", ".join(item.get("technology", [])[:6]) or "Not available"
            lines.append(f"{item['role']}: key skills {skills}. Technology examples {tech}.")
        return "\n".join(lines)
    if any(token in normalized_question for token in ("what", "do", "responsib", "day to day", "job")):
        lines = []
        for item in career_intel:
            tasks = "; ".join(item.get("on_the_job", [])[:3]) or "Task details unavailable."
            lines.append(f"{item['role']}: {item.get('what_they_do', '')} Day-to-day examples: {tasks}")
        return "\n".join(lines)

    lines = []
    for item in career_intel:
        lines.append(
            f"{item['role']}: {item.get('what_they_do', '')} "
            f"Education: {item.get('education', 'Unavailable')}. "
            f"Outlook: {item.get('outlook', 'Unavailable')}."
        )
    return "\n".join(lines)
