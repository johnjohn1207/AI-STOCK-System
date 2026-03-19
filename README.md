# 📈 AI-Driven Quantitative Trading System (全端量化交易與回測系統)

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Advanced-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen)

## 📝 專案簡介 (Project Overview)
本專案為一個完整的**資料驅動 (Data-Driven) 量化交易系統**。打破傳統單純使用 Python 腳本跑回測的限制，本系統導入了**三層式架構 (Three-Tier Architecture)**，將前端視覺化、後端演算法與資料庫深度整合。系統涵蓋了自動化 ETL 資料清洗、LSTM 深度學習預測、技術指標多因子濾網，以及具備 ACID 交易保護的實盤模擬下單機制。

本系統的設計初衷在於展現跨領域整合能力：**將財務金融的量化邏輯，透過嚴謹的軟體工程規範 (模組化、單元測試、防呆機制) 進行系統化實作。**

## 🏗️ 系統架構與技術棧 (Architecture & Tech Stack)

graph LR
    %% 外部依賴
    YF[Yahoo Finance API] -->|即時/歷史報價| ETL[data_loader.py <br> ETL & 增量更新]
    
    %% 資料庫中心
    subgraph DB [PostgreSQL 核心資料庫]
        MD[Market_Data <br> 乾淨數據與技術指標]
        MS[Model_Signals <br> AI 預測與交易訊號]
        TR[Transactions <br> 資金帳本與庫存]
    end
    
    %% 資料流
    ETL -->|寫入數據| MD
    AI[model_core.py <br> LSTM 模型] -->|讀取特徵| MD
    AI -->|寫入預測結果| MS
    BT[backtest_core.py <br> 回測引擎] -->|撈取歷史訊號| MD
    Daily[daily_trader.py <br> 自動下單排程] -->|讀取最新訊號| MS
    Daily <-->|驗證餘額與扣款| TR
    
    %% 前端展示
    UI[Streamlit app.py <br> 前端 UI] <-->|快取讀取與渲染| BT
    
    style Daily fill:#f9f,stroke:#333,stroke-width:2px
    style DB fill:#e6f3ff,stroke:#333,stroke-width:2px

graph TD
    A[每日排程啟動 Daily Trader] --> B{檢查最新資料與模型訊號}
    B -- 買進 (BUY) --> C[查詢 DB 可用資金餘額]
    C --> D{餘額 > 股價？}
    D -- 否 --> E[資金不足，警告並取消委託]
    D -- 是 --> F[動態精算可買股數，執行 ExecuteTrade]
    
    B -- 賣出 (SELL) --> G[查詢 DB 目前庫存]
    G --> H{庫存 > 0？}
    H -- 否 --> I[無庫存，忽略賣出訊號]
    H -- 是 --> J[全數出清，執行 ExecuteTrade]
    
    F --> K[紀錄 Transaction 並更新 Model_Signals]
    J --> K
    E --> K
    I --> K

本系統嚴格遵守「關注點分離 (Separation of Concerns)」原則，分為三大層：

1. **展示層 (Presentation Layer)**: `Streamlit`, `Plotly`
   - 提供 RWD 互動式網頁介面，支援動態資產曲線縮放與 AI 預測儀表板。
2. **邏輯層 (Business Logic Layer)**: `PyTorch (LSTM)`, `Pandas`, `NumPy`
   - 包含回測引擎 (`backtest_core.py`) 與 AI 模型特徵工程 (`model_core.py`)。
   - 導入 **TDD (測試驅動開發)**，使用 `pytest` 確保核心財務指標(如最大回撤、夏普值)計算之絕對準確與極端值防護。
3. **資料層 (Data Access Layer)**: `PostgreSQL`, `SQLAlchemy`, `yfinance`
   - 捨棄 CSV，全面採用關聯式資料庫。實作 **Stored Procedures (預存程序)** 處理交易扣款，確保資金變動符合 ACID 特性，杜絕負庫存與超額買進。

## ✨ 核心亮點功能 (Key Features)

- **自動化 ETL 與抗錯機制**: `data_loader.py` 動態介接外部 API，自動對齊真實交易日，處理 Missing Data 並動態計算技術指標 (RSI, MA20)，直接餵入模型。
- **雙因子進出場邏輯**: 結合 LSTM 明日漲跌預測與傳統技術指標濾網，建構高勝率的交易策略。
- **動態資金與部位控管**: `daily_trader.py` 模擬實盤排程機器人，下單前自動向資料庫核實 `Users` 餘額與 `Transactions` 庫存，精算可購買股數。
- **模組化與型別提示**: 核心程式碼全面導入 Python Type Hinting (`typing`) 與 Google Style Docstrings，具備極高的可讀性與擴充性。

## 🚀 快速啟動 (Quick Start)

### 1. 環境建置
請確保本機端已安裝 PostgreSQL，並建立名為 `quant_db` 的資料庫。
```bash
# 安裝依賴套件
pip install -r requirements.txt
2. 啟動前端展示介面 (Backtest UI)
Bash
streamlit run app.py
3. 執行單元測試 (Unit Testing)
Bash
pytest unit_test.py
📂 專案結構 (Project Structure)
├── app.py # Streamlit 前端主程式
├── data_loader.py # ETL 與資料庫介接模組
├── model_core.py # 深度學習模型與特徵工程
├── backtest_core.py # 回測引擎與績效結算模組
├── daily_trader.py # 模擬實盤自動化下單腳本
└── unit_test.py # Pytest 單元測試腳本