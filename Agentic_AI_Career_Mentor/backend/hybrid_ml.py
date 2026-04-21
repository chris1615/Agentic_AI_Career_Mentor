"""
hybrid_ml.py
------------
Random Forest training and inference for hybrid role prediction.
"""

from __future__ import annotations

import os
from typing import Any

from semantic_engine import encode_text, normalize, role_text

try:
    import joblib
except ImportError:  # pragma: no cover - optional dependency
    joblib = None

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.model_selection import train_test_split
except ImportError:  # pragma: no cover - optional dependency
    RandomForestClassifier = None
    accuracy_score = None
    confusion_matrix = None
    train_test_split = None


MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "career_random_forest.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "career_random_forest_metadata.joblib")

_MODEL_CACHE = None
_METADATA_CACHE = None


def _build_training_samples(role_name: str, role_data: dict[str, Any]) -> list[str]:
    skills = role_data.get("skills", []) or []
    description = role_data.get("description", "")
    domain = role_data.get("domain", "")
    roadmap = role_data.get("roadmap", []) or []

    samples = [
        ", ".join(skills),
        f"{role_name}. {description}",
        f"{domain}. {', '.join(skills)}",
        f"{role_name}. Domain: {domain}. Skills: {', '.join(skills)}",
        f"{role_name}. Roadmap: {', '.join(roadmap[:4])}",
        role_text(role_name, role_data),
    ]
    return [sample.strip() for sample in samples if sample.strip()]


def _vectorize_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        embedding = encode_text(text)
        if embedding is not None:
            vectors.append(embedding)
    return vectors


def _artifacts_are_usable() -> bool:
    return all(
        [
            joblib is not None,
            RandomForestClassifier is not None,
            accuracy_score is not None,
            confusion_matrix is not None,
            train_test_split is not None,
        ]
    )


def train_or_load_model(roles: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    global _MODEL_CACHE, _METADATA_CACHE

    if _MODEL_CACHE is not None and _METADATA_CACHE is not None:
        return _MODEL_CACHE, _METADATA_CACHE

    if not _artifacts_are_usable():
        _MODEL_CACHE = None
        _METADATA_CACHE = {
            "status": "unavailable",
            "accuracy": None,
            "confusion_matrix": [],
            "labels": [],
            "feature_source": "sentence-transformer embeddings",
        }
        return _MODEL_CACHE, _METADATA_CACHE

    os.makedirs(MODEL_DIR, exist_ok=True)

    if os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH):
        try:
            _MODEL_CACHE = joblib.load(MODEL_PATH)
            _METADATA_CACHE = joblib.load(METADATA_PATH)
            return _MODEL_CACHE, _METADATA_CACHE
        except Exception:
            pass

    train_vectors: list[list[float]] = []
    train_labels: list[str] = []
    for role_name, role_data in roles.items():
        samples = _build_training_samples(role_name, role_data)
        vectors = _vectorize_texts(samples)
        for vector in vectors:
            train_vectors.append(vector)
            train_labels.append(role_name)

    unique_labels = sorted(set(train_labels))
    if len(unique_labels) < 2 or len(train_vectors) < 4:
        _MODEL_CACHE = None
        _METADATA_CACHE = {
            "status": "insufficient_data",
            "accuracy": None,
            "confusion_matrix": [],
            "labels": unique_labels,
            "feature_source": "sentence-transformer embeddings",
        }
        return _MODEL_CACHE, _METADATA_CACHE

    try:
        x_train, x_test, y_train, y_test = train_test_split(
            train_vectors,
            train_labels,
            test_size=0.25,
            random_state=42,
            stratify=train_labels,
        )
    except ValueError:
        x_train, x_test, y_train, y_test = train_test_split(
            train_vectors,
            train_labels,
            test_size=0.25,
            random_state=42,
        )

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=14,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    metadata = {
        "status": "trained",
        "accuracy": float(accuracy_score(y_test, predictions)),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=unique_labels).tolist(),
        "labels": unique_labels,
        "feature_source": "sentence-transformer embeddings",
        "sample_count": len(train_vectors),
    }

    joblib.dump(model, MODEL_PATH)
    joblib.dump(metadata, METADATA_PATH)

    _MODEL_CACHE = model
    _METADATA_CACHE = metadata
    return _MODEL_CACHE, _METADATA_CACHE


def predict_role_probabilities(
    *,
    user_skills: list[str],
    interests: str,
    career_goal: str,
    roles: dict[str, Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    model, metadata = train_or_load_model(roles)
    if model is None:
        return {}, metadata

    user_profile_text = ". ".join(
        part
        for part in [
            f"Skills: {', '.join(user_skills)}" if user_skills else "",
            f"Interests: {interests}" if interests else "",
            f"Career Goal: {career_goal}" if career_goal else "",
        ]
        if part
    )
    embedding = encode_text(user_profile_text)
    if embedding is None:
        return {}, metadata

    try:
        probabilities = model.predict_proba([embedding])[0]
    except Exception:
        return {}, metadata

    by_role = {}
    for label, probability in zip(model.classes_, probabilities):
        by_role[str(label)] = float(probability)

    normalized = {normalize(role_name): score for role_name, score in by_role.items()}
    final = {}
    for role_name in roles:
        final[role_name] = normalized.get(normalize(role_name), 0.0)

    return final, metadata
