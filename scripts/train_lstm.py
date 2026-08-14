"""Train and publish an LSTM artifact.

Usage:
  python scripts/train_lstm.py --ticker 2330.TW --epochs 30 --output /tmp/model.pth

The API never trains a model. Run this script as a scheduled/manual training job.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model_core import LSTMModel  # noqa: E402
from model_registry import ModelMetadata, save_artifact  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--output", default="/tmp/lstm_model.pth")
    args = parser.parse_args()

    # This command is intentionally the deployment boundary. The existing
    # project training pipeline should write the trained state_dict to --output.
    # Keeping the artifact publication separate makes scheduled retraining safe.
    model = LSTMModel(input_size=4, hidden_size=64, num_layers=2)
    raise SystemExit(
        "Training CLI scaffold created. Connect the existing data/training loop here "
        "before publishing a production artifact; the API remains inference-only."
    )


if __name__ == "__main__":
    main()
