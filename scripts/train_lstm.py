"""Train and publish a versioned LSTM artifact.

Example:
  python scripts/train_lstm.py --ticker 2330.TW --start 2020-01-01 --end 2026-01-01 --epochs 30

Run this as a scheduled/manual training job. The FastAPI request path does not train.
"""

from __future__ import annotations

import argparse
import pickle
import sys
import tempfile
from pathlib import Path

import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model_core import prepare_model_data, train_lstm_model  # noqa: E402
from model_registry import save_artifacts  # noqa: E402
from api.main import build_model_features, get_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

FEATURES = ["Return", "Close", "Volume", "RSI"]
LOOK_BACK = 60


def load_training_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    query = text("""
        SELECT trade_date, close_price, volume
        FROM Market_Data
        WHERE ticker_symbol = :ticker
          AND trade_date >= :start
          AND trade_date <= :end
        ORDER BY trade_date ASC
    """)
    engine = get_engine()
    try:
        with engine.connect() as conn:
            raw = pd.read_sql(query, conn, params={"ticker": ticker, "start": start, "end": end})
    finally:
        engine.dispose()
    return build_model_features(raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2099-12-31")
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()

    df = load_training_data(args.ticker, args.start, args.end)
    if len(df) <= LOOK_BACK + 10:
        raise SystemExit("Training data is insufficient; need more than 70 valid rows.")

    X, y, scaler, _ = prepare_model_data(df, look_back=LOOK_BACK)
    train_size = max(1, int(len(X) * 0.8))
    model, _ = train_lstm_model(X[:train_size], y[:train_size], epochs=args.epochs)

    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / "model.pth"
        scaler_path = Path(tmp) / "scaler.pkl"
        torch.save(model.cpu().state_dict(), model_path)
        with scaler_path.open("wb") as handle:
            pickle.dump(scaler, handle)
        metadata = save_artifacts(model_path, scaler_path, args.ticker, LOOK_BACK, FEATURES, args.epochs)

    print(f"Published LSTM {metadata.version} for {metadata.ticker}: {metadata.artifact}")


if __name__ == "__main__":
    main()
