"""Persistent model artifacts and metadata for production inference."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
REGISTRY_FILE = MODEL_DIR / "registry.json"


@dataclass(frozen=True)
class ModelMetadata:
    model_name: str
    version: str
    ticker: str
    look_back: int
    features: list[str]
    trained_at: str
    epochs: int
    artifact: str
    scaler_artifact: str


def _load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {"models": []}
    return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))


def _save_registry(registry: dict) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_FILE)


def save_artifacts(model_source: str | Path, scaler_source: str | Path, ticker: str, look_back: int, features: list[str], epochs: int) -> ModelMetadata:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_ticker = ticker.replace("/", "_")
    target = MODEL_DIR / f"lstm_{safe_ticker}_{version}.pth"
    scaler_target = MODEL_DIR / f"lstm_{safe_ticker}_{version}.scaler.pkl"
    shutil.copy2(model_source, target)
    shutil.copy2(scaler_source, scaler_target)
    metadata = ModelMetadata(
        model_name="lstm",
        version=version,
        ticker=ticker,
        look_back=look_back,
        features=features,
        trained_at=datetime.now(timezone.utc).isoformat(),
        epochs=epochs,
        artifact=str(target),
        scaler_artifact=str(scaler_target),
    )
    registry = _load_registry()
    registry.setdefault("models", []).append(asdict(metadata))
    registry["active"] = asdict(metadata)
    _save_registry(registry)
    return metadata


def get_active(ticker: str | None = None) -> ModelMetadata | None:
    registry = _load_registry()
    active = registry.get("active")
    if not active or (ticker and active.get("ticker") != ticker):
        return None
    return ModelMetadata(**active)


def list_models() -> list[ModelMetadata]:
    return [ModelMetadata(**item) for item in _load_registry().get("models", [])]
