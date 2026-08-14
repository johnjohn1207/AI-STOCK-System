import os
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

import backtest_core
import model_core

load_dotenv()

app = FastAPI(title="AI Stock System API", version="1.2.0")

# Railway/Vercel are separate origins in production. Set CORS_ORIGINS to a
# comma-separated list, e.g. https://ai-stock-system.vercel.app,http://localhost:3000.
configured_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
allow_all_origins = configured_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BacktestRequest(BaseModel):
    ticker: str = Field(default="2330.TW", min_length=1, max_length=20)
    start_date: date = date(2022, 1, 1)
    end_date: date = date.today()
    initial_capital: float = Field(default=100000, ge=10000)
    stop_loss: float = Field(default=0.05, gt=0, le=0.2)
    take_profit: float = Field(default=0.15, gt=0, le=0.5)
    train_epochs: int = Field(default=30, ge=1, le=200)


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Supabase commonly supplies postgres:// or postgresql:// URLs.
        if database_url.startswith("postgres://"):
            database_url = "postgresql+psycopg2://" + database_url[len("postgres://"):]
        elif database_url.startswith("postgresql://"):
            database_url = "postgresql+psycopg2://" + database_url[len("postgresql://"):]
        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=3,
            max_overflow=2,
        )

    values = [os.getenv(key) for key in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")]
    if not all(values):
        raise HTTPException(status_code=500, detail="Database environment variables are incomplete")
    user, password, host, port, name = values
    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}",
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=3,
        max_overflow=2,
    )


def fetch_market_data(request: BacktestRequest) -> pd.DataFrame:
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
            return pd.read_sql(
                query,
                conn,
                params={
                    "ticker": request.ticker,
                    "start": request.start_date,
                    "end": request.end_date,
                },
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc
    finally:
        engine.dispose()


def build_model_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["Return"] = result["close_price"].pct_change()
    result["MA20"] = result["close_price"].rolling(20).mean()
    result["Vol_MA20"] = result["volume"].rolling(20).mean()
    result["Factor_Pass"] = (
        (result["close_price"] > result["MA20"])
        & (result["volume"] > result["Vol_MA20"])
    )

    delta = result["close_price"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    result["RSI"] = (100 - (100 / (1 + rs))).fillna(50)
    return result.dropna(subset=["Return", "MA20", "Vol_MA20"]).reset_index(drop=True)


def generate_lstm_signals(df: pd.DataFrame, epochs: int) -> tuple[np.ndarray, np.ndarray]:
    look_back = 60
    if len(df) <= look_back + 10:
        raise HTTPException(status_code=400, detail="資料不足：LSTM 至少需要 71 筆以上有效資料")

    X, y, scaler, _ = model_core.prepare_model_data(df, look_back=look_back)
    if len(X) < 10:
        raise HTTPException(status_code=400, detail="有效訓練資料不足，無法建立 LSTM 訊號")

    train_size = max(1, int(len(X) * 0.8))
    model, device = model_core.train_lstm_model(X[:train_size], y[:train_size], epochs=epochs)
    predictions = model_core.predict_model(model, X, device).reshape(-1)
    predicted_returns = model_core.get_inverse_price(predictions, scaler, feature_count=4)

    signal_series = np.zeros(len(df), dtype=bool)
    signal_series[look_back:] = predicted_returns > 0
    return signal_series, predicted_returns


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_health() -> dict[str, str]:
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    finally:
        engine.dispose()


@app.post("/api/backtest")
def run_backtest(request: BacktestRequest) -> dict[str, Any]:
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="開始日期不可晚於結束日期")

    raw_df = fetch_market_data(request)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="找不到指定股票與日期範圍的資料")

    df = build_model_features(raw_df)
    if len(df) <= 70:
        raise HTTPException(status_code=400, detail="資料不足，請擴大回測日期範圍")

    final_signals, predicted_returns = generate_lstm_signals(df, request.train_epochs)
    factor_pass = df["Factor_Pass"].to_numpy(dtype=bool)
    final_signals &= factor_pass

    dates = df["trade_date"].tolist()
    prices = df["close_price"].to_numpy(dtype=float)
    ma20 = df["MA20"].to_numpy(dtype=float)

    final_capital, equity_curve, trade_log, trade_profits = backtest_core.run_backtest(
        test_dates=dates,
        backtest_prices=prices,
        final_signals=final_signals,
        ma20_data=ma20,
        factor_pass_data=factor_pass,
        initial_capital=request.initial_capital,
        stop_loss_pct=request.stop_loss,
        take_profit_pct=request.take_profit,
    )
    metrics = backtest_core.calculate_metrics(request.initial_capital, final_capital, equity_curve, trade_profits)

    trades = [
        {
            "date": pd.Timestamp(row[0]).strftime("%Y-%m-%d"),
            "action": str(row[1]),
            "price": float(row[2]),
            "balance": float(row[3]),
            "shares": int(row[4]),
        }
        for row in trade_log
    ]

    prediction_dates = dates[60:]
    return {
        "ticker": request.ticker,
        "model": "LSTM",
        "lookBack": 60,
        "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates],
        "prices": prices.tolist(),
        "equity_curve": [float(x) for x in equity_curve],
        "signals": [bool(x) for x in final_signals],
        "predicted_returns": [float(x) for x in predicted_returns],
        "prediction_dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in prediction_dates],
        "metrics": {
            "totalReturn": float(metrics["Total Return (%)"]),
            "winRate": float(metrics["Win Rate (%)"]),
            "maxDrawdown": float(metrics["Max Drawdown (%)"]),
            "sharpe": float(metrics["Sharpe Ratio"]),
        },
        "trades": trades,
    }
