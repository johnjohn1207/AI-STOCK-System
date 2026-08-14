# 📈 AI-Driven Quantitative Trading System

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Advanced-blue)
![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen)

## 📝 專案簡介

這是一套資料驅動的全端量化交易與回測系統。前端已由 Streamlit 升級為 **Next.js + React**，Python 則透過 **FastAPI** 提供回測 API；核心策略與 PostgreSQL 資料層維持原有設計。

目前 Dashboard 保留原 Streamlit 版的主要功能：股票與日期範圍設定、初始本金、停損/停利、KPI、資金曲線、買賣點與交易日誌。

## 🏗️ 新架構

```mermaid
graph LR
    WEB[Next.js + React\nResponsive Dashboard] -->|POST /api/backtest| API[FastAPI\nPython API]
    API --> BT[backtest_core.py\n回測引擎]
    API --> DB[(PostgreSQL\nMarket_Data)]
    ETL[data_loader.py] --> DB
    MODEL[model_core.py\nLSTM] --> DB
    TRADER[daily_trader.py] --> DB
```

### 技術分層

1. **Presentation Layer** — `frontend/`
   - Next.js App Router、React、TypeScript、Recharts。
   - RWD Dashboard，取代原本的 Streamlit UI。
2. **API / Application Layer** — `api/main.py`
   - FastAPI 接收回測參數、查詢 PostgreSQL、呼叫核心回測引擎並回傳 JSON。
   - API 與前端分離，之後可直接接手機 App、其他 Web Client 或自動化服務。
3. **Business Logic Layer** — `backtest_core.py`, `model_core.py`
   - 保留既有 Python 回測與 AI 模型邏輯。
4. **Data Layer** — PostgreSQL / SQLAlchemy / `data_loader.py`
   - 歷史市場資料集中由 PostgreSQL 管理。

## 🚀 快速啟動

### 1. Python API

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 2. Next.js 前端

```bash
cd frontend
npm install
npm run dev
```

瀏覽器開啟 `http://localhost:3000`。

若 FastAPI 不是跑在 `http://localhost:8000`，可設定：

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. PostgreSQL

請確認 `.env` 已設定：

```text
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
DB_NAME=quant_db
```

### 4. 單元測試

```bash
pytest unit_test.py
```

## 📂 專案結構

```text
├── api/
│   └── main.py            # FastAPI 回測 API
├── frontend/
│   ├── app/
│   │   ├── page.tsx       # Next.js Dashboard
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   └── next-env.d.ts
├── data_loader.py         # ETL 與資料庫介接
├── model_core.py          # LSTM 模型與特徵工程
├── backtest_core.py       # 回測引擎與績效結算
├── daily_trader.py        # 模擬實盤自動化下單
├── requirements.txt       # Python API / ML 依賴
└── unit_test.py            # Pytest 單元測試
```

## ⚠️ AI 訊號說明

目前 API 為了維持原 Streamlit Demo 的展示行為，使用固定 seed 的隨機訊號模擬 AI 預測；正式環境應將 `api/main.py` 中的 `final_signals` 替換為 `model_core` 的實際 LSTM 預測結果。這樣前端不需要再修改，只需替換後端模型來源即可。
