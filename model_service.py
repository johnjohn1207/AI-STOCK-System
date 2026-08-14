"""Production LSTM inference helpers.

The API only loads a published artifact. Training is handled by a separate job.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import torch

from model_core import LSTMModel
from model_registry import ModelMetadata, get_active

FEATURES = ["Return", "Close", "Volume", "RSI"]


def _model_from_artifact(path: str | Path) -> LSTMModel:
    model = LSTMModel(input_size=4, hidden_size=50, num_layers=2, dropout=0.2)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


def load_scaler(metadata: ModelMetadata):
    with open(metadata.scaler_artifact, "rb") as handle:
        return pickle.load(handle)


def make_sequences(df, metadata: ModelMetadata) -> np.ndarray:
    scaler = load_scaler(metadata)
    values = df[metadata.features].to_numpy(dtype=np.float32)
    scaled = scaler.transform(values)
    if len(scaled) <= metadata.look_back:
        return np.empty((0, metadata.look_back, len(metadata.features)), dtype=np.float32)
    return np.asarray(
        [scaled[i - metadata.look_back:i] for i in range(metadata.look_back, len(scaled))],
        dtype=np.float32,
    )


def predict_returns(X: np.ndarray, metadata: ModelMetadata) -> np.ndarray:
    model = _model_from_artifact(metadata.artifact)
    scaler = load_scaler(metadata)
    tensor = torch.from_numpy(X).float()
    with torch.inference_mode():
        scaled_predictions = model(tensor).cpu().numpy().reshape(-1)
    dummy = np.zeros((len(scaled_predictions), len(metadata.features)), dtype=np.float32)
    dummy[:, 0] = scaled_predictions
    return scaler.inverse_transform(dummy)[:, 0]


def active_model(ticker: str) -> ModelMetadata | None:
    return get_active(ticker)
