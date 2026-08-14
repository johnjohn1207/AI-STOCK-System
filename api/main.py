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

load_dotenv()

app = FastAPI(title="AI Stock System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


def get_engine():
    values = [os.getenv(key) for key in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")]
    if not all(values):
        raise HTTPException(status_code=500, detail="Database environment variables are incomplete")
    user, password, host, port, name = values
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/backtest")
def run_backtest(request: BacktestRequest) -> dict[str, Any]:
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="開始日期不可晚於結束日期")

    df = fetch_market_data(request)
    if df.empty:
        raise HTTPException(status_code=404, detail="找不到指定股票與日期範圍的資料")

    df["ma20"] = df["close_price"].rolling(window=20).mean().bfill()
    volume_avg = df["volume"].rolling(20).mean()
    df["factor_pass"] = (df["volume"] > volume_avg).fillna(False)

    # 保留原 Streamlit 展示版的 AI 訊號行為；正式模型接入時可替換成 model_core.predict(df)。
    rng = np.random.default_rng(42)
    final_signals = rng.choice([True, False], size=len(df), p=[0.3, 0.7])

    dates = df["trade_date"].tolist()
    prices = df["close_price"].to_numpy()

    final_capital, equity_curve, trade_log, trade_profits = backtest_core.run_backtest(
        test_dates=dates,
        backtest_prices=prices,
        final_signals=final_signals,
        ma20_data=df["ma20"].to_numpy(),
        factor_pass_data=df["factor_pass"].to_numpy(),
        initial_capital=request.initial_capital,
        stop_loss_pct=request.stop_loss,
        take_profit_pct=request.take_profit,
    )
    metrics = backtest_core.calculate_metrics(
        request.initial_capital, final_capital, equity_curve, trade_profits
    )

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

    return {
        "ticker": request.ticker,
        "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates],
        "prices": [float(x) for x in prices],
        "equity_curve": [float(x) for x in equity_curve],
        "metrics": {
            "totalReturn": float(metrics["Total Return (%)"]),
            "winRate": float(metrics["Win Rate (%)"]),
            "maxDrawdown": float(metrics["Max Drawdown (%)"]),
            "sharpe": float(metrics["Sharpe Ratio"]),
        },
        "trades": trades,
    }
