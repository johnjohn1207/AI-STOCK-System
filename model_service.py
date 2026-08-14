"""Production LSTM training/inference helpers.

Training is explicit; API inference only loads an existing artifact.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from sklearn.preprocessing import MinMaxScaler

from model_core import LSTMModel
from model_registry import ModelMetadata, get_active, save_artifact

FEATURES = ["Return", "Close", "Volume", "RSI"]
LOOK_BACK = 60


def _model_from_artifact(path: str | Path) -> LSTMModel:
    model = LSTMModel(input_size=len(FEATURES), hidden_size=64, num_layers=2)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


def predict_return(sequence: np.ndarray, metadata: ModelMetadata) -> float:
    model = _model_from_artifact(metadata.artifact)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(sequence.astype(np.float32))
    x = torch.tensor(scaled[-metadata.look_back:], dtype=torch.float32).unsqueeze(0)
    with torch.inference_mode():
        scaled_prediction = float(model(x).squeeze().item())
    # The saved model predicts the scaled Return target. Inference uses the
    # training-window scaler as a local approximation until a fitted scaler
    # artifact is persisted alongside the model.
    low, high = scaler.data_min_[0], scaler.data_max_[0]
    return float(scaled_prediction * (high - low) + low)


def active_model(ticker: str) -> ModelMetadata | None:
    return get_active(ticker)
