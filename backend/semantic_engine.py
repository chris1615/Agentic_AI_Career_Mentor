"""
semantic_engine.py
------------------
Sentence-transformer utilities with cached role embeddings.
"""

from __future__ import annotations

import math
import re
from typing import Any

MODEL_NAME = "all-MiniLM-L6-v2"

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False
_ROLE_EMBEDDING_CACHE: dict[str, dict[str, list[float] | str]] = {}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9.+#/-]+", normalize(text)) if token}


def role_text(role_name: str, role_data: dict[str, Any]) -> str:
    skills = ", ".join(role_data.get("skills", []) or [])
    description = role_data.get("description", "")
    domain = role_data.get("domain", "")
    return f"{role_name}. Domain: {domain}. Skills: {skills}. Description: {description}".strip()


def load_sentence_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED

    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _MODEL = SentenceTransformer(MODEL_NAME)
    except Exception:
        _MODEL = None

    return _MODEL


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(vec_a, vec_b))
    denom_a = math.sqrt(sum(a * a for a in vec_a))
    denom_b = math.sqrt(sum(b * b for b in vec_b))
    if denom_a == 0 or denom_b == 0:
        return 0.0
    return numerator / (denom_a * denom_b)


def fallback_similarity(text_a: str, text_b: str) -> float:
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / math.sqrt(len(tokens_a) * len(tokens_b))


def encode_text(text: str) -> list[float] | None:
    model = load_sentence_model()
    if model is None:
        return None

    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return [float(value) for value in embedding]
    except Exception:
        return None


def semantic_similarity(text_a: str, text_b: str) -> float:
    text_a = (text_a or "").strip()
    text_b = (text_b or "").strip()

    if not text_a or not text_b:
        return 0.0
    if normalize(text_a) == normalize(text_b):
        return 1.0

    embedding_a = encode_text(text_a)
    embedding_b = encode_text(text_b)
    if embedding_a is None or embedding_b is None:
        return max(0.0, min(1.0, fallback_similarity(text_a, text_b)))

    similarity = cosine_similarity(embedding_a, embedding_b)
    return max(0.0, min(1.0, similarity))


def get_role_embedding(role_name: str, role_data: dict[str, Any]) -> list[float] | None:
    cache_key = normalize(role_name)
    cache_signature = role_text(role_name, role_data)
    cached = _ROLE_EMBEDDING_CACHE.get(cache_key)
    if cached and cached.get("signature") == cache_signature:
        return cached.get("embedding")  # type: ignore[return-value]

    embedding = encode_text(cache_signature)
    if embedding is None:
        return None

    _ROLE_EMBEDDING_CACHE[cache_key] = {
        "signature": cache_signature,
        "embedding": embedding,
    }
    return embedding

def warm_role_embeddings(roles: dict[str, dict[str, Any]] | list[dict[str, Any]]) -> None:
    """
    Pre-compute and cache embeddings for all roles.

    Accepts EITHER:
      - a list of role dicts  (new data_loader format)
      - a dict  {role_name: role_data}  (old format)
    """
    if isinstance(roles, list):
        roles = {r.get("role", f"role_{i}"): r for i, r in enumerate(roles)}

    for role_name, role_data in roles.items():
        normalized_role = dict(role_data)
        if "skills" in normalized_role and "required_skills" not in normalized_role:
            normalized_role["required_skills"] = normalized_role.get("skills", [])
        get_role_embedding(role_name, normalized_role)
