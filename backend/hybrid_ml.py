"""
hybrid_ml.py
------------
Trains (or reloads) a Random Forest classifier on the merged roles dataset
and exposes a simple predict interface used by recommendation_engine.py.

Model artefact
--------------
    models/random_forest_model.pkl

The model is retrained when:
    * The pkl file does not exist yet.
    * ``force_retrain=True`` is passed to ``get_rf_model()``.
    * The module is executed directly (``python -m backend.hybrid_ml``).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

_HERE       = Path(__file__).parent
_MODEL_DIR  = _HERE.parent / "models"
_MODEL_FILE = _MODEL_DIR / "random_forest_model.pkl"

# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer
    _sbert = SentenceTransformer("all-MiniLM-L6-v2")
    _SBERT_AVAILABLE = True
except ImportError:
    _SBERT_AVAILABLE = False


def _embed(text: str) -> np.ndarray:
    if _SBERT_AVAILABLE:
        return _sbert.encode(text, normalize_embeddings=True)
    # Fallback: simple character-hash bag-of-words (64 dims)
    vec = np.zeros(64)
    for i, ch in enumerate(text.lower()):
        vec[ord(ch) % 64] += 1
    norm = np.linalg.norm(vec) or 1.0
    return vec / norm


def _role_to_features(role: dict[str, Any]) -> np.ndarray:
    """Convert a role dict to a fixed-length feature vector."""
    skills_text = " ".join(role.get("required_skills", []))
    desc_text   = role.get("description", "")
    combined    = f"{skills_text} {desc_text}"
    return _embed(combined)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(
    roles: list[dict[str, Any]],
    *,
    n_estimators: int = 200,
    random_state: int = 42,
) -> RandomForestClassifier:
    """
    Train a Random Forest to predict role domain from role features.

    Parameters
    ----------
    roles : merged role list from data_loader.load_roles()

    Returns
    -------
    Fitted RandomForestClassifier (also saved to disk).
    """
    if len(roles) < 4:
        raise ValueError(
            f"Need at least 4 roles to train; got {len(roles)}. "
            "Run dynamic_role_builder to expand the dataset."
        )

    X = np.array([_role_to_features(r) for r in roles])
    le = LabelEncoder()
    y  = le.fit_transform([r.get("domain", "General") for r in roles])

    # Guard against degenerate splits
    n_splits = min(2, len(np.unique(y)))
    if n_splits < 2 or len(roles) < 6:
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=random_state, stratify=y
        )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=10,
        random_state=random_state,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    train_acc = clf.score(X_train, y_train)
    test_acc  = clf.score(X_test,  y_test)
    logger.info(
        "RF trained on %d samples | train_acc=%.3f | test_acc=%.3f",
        len(X_train), train_acc, test_acc,
    )

    # Persist
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"model": clf, "label_encoder": le}
    joblib.dump(payload, _MODEL_FILE)
    logger.info("Model saved to %s", _MODEL_FILE)
    return clf


# ---------------------------------------------------------------------------
# Public accessor
# ---------------------------------------------------------------------------

_cached_model: RandomForestClassifier | None = None


def get_rf_model(
    roles: list[dict[str, Any]] | None = None,
    force_retrain: bool = False,
) -> RandomForestClassifier | None:
    """
    Return a trained RandomForestClassifier.

    * Loads from disk if available and ``force_retrain`` is False.
    * Trains from scratch if no saved model exists (requires *roles*).
    * Returns ``None`` if training is impossible (no roles provided).
    """
    global _cached_model

    if not force_retrain and _cached_model is not None:
        return _cached_model

    if not force_retrain and _MODEL_FILE.exists():
        try:
            payload = joblib.load(_MODEL_FILE)
            _cached_model = payload["model"]
            logger.info("RF model loaded from %s", _MODEL_FILE)
            return _cached_model
        except Exception as exc:
            logger.warning("Could not load saved model (%s); retraining.", exc)

    if not roles:
        logger.warning("No roles supplied; cannot train RF model.")
        return None

    try:
        _cached_model = train_model(roles)
        return _cached_model
    except ValueError as exc:
        logger.warning("RF training skipped: %s", exc)
        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from backend.data_loader import load_roles

    all_roles = load_roles()
    print(f"Dataset size: {len(all_roles)} roles")
    model = get_rf_model(roles=all_roles, force_retrain=True)
    if model:
        print("Training complete. Model saved to models/random_forest_model.pkl")
    else:
        print("Training failed – check logs for details.")
