import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 載入你精心撰寫的核心模組
import backtest_core
# import model_core  # 這裡保留給你呼叫 LSTM 模型預測使用

# ==========================================
# 🛡️ 系統初始化與環境變數 (保護資安)
# ==========================================
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# ==========================================
# 🚀 效能優化層：資料庫連線與 In-memory Cache
# ==========================================
@st.cache_data(ttl=3600)
def fetch_data_from_db(ticker: str, start_date, end_date) -> pd.DataFrame:
    """從 PostgreSQL 撈取歷史資料並快取於記憶體中 (1小時)"""
    db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # 使用參數綁定防禦 SQL Injection
        query = text("""
            SELECT trade_date, close_price, volume 
            FROM Market_Data 
            WHERE ticker_symbol = :ticker 
              AND trade_date >= :start 
              AND trade_date <= :end 
            ORDER BY trade_date ASC
        """)
        df = pd.read_sql(query, conn, params={"ticker": ticker, "start": start_date, "end": end_date})
    return df

# ==========================================
# 🎨 展示層：Streamlit 網頁主程式
# ==========================================
def main():
    # 設定網頁標籤與版面寬度
    st.set_page_config(page_title="AI 量化交易系統", page_icon="📈", layout="wide")
    st.title("📈 AI-Driven 雙因子量化回測系統")
    st.markdown("本系統展示了跨領域整合能力：結合 **LSTM 深度學習、PostgreSQL 資料庫與 Plotly 互動視覺化**。")

    # --- [側邊欄：回測參數設定] ---
    st.sidebar.header("⚙️ 交易策略參數")
    ticker = st.sidebar.text_input("股票代號", "2330.TW")
    start_date = st.sidebar.date_input("開始日期", pd.to_datetime("2022-01-01"))
    end_date = st.sidebar.date_input("結束日期", pd.to_datetime("today"))
    
    st.sidebar.markdown("---")
    initial_capital = st.sidebar.number_input("初始本金 (元)", min_value=10000, value=100000, step=10000)
    stop_loss = st.sidebar.slider("停損百分比 (%)", 1, 20, 5) / 100.0
    take_profit = st.sidebar.slider("停利百分比 (%)", 1, 50, 15) / 100.0

    # 當使用者點擊「開始回測」按鈕
    if st.sidebar.button("🚀 執行全端系統回測"):
        with st.spinner("連接資料庫與執行 AI 模型中..."):
            
            # 1. 取得歷史資料 (毫秒級快取)
            df = fetch_data_from_db(ticker, start_date, end_date)
            
            if df.empty:
                st.error("❌ 找不到資料，請確認 PostgreSQL 資料庫中是否有該檔股票的紀錄。")
                return

            # --- [模擬：特徵工程與 AI 預測] ---
            # 實務上這裡會呼叫你的 model_core，例如： final_signals = model_core.predict(df)
            # 為了確保系統順暢展示，我們在這裡計算簡單的 MA20 並模擬 AI 訊號
            df['ma20'] = df['close_price'].rolling(window=20).mean().fillna(method='bfill')
            df['factor_pass'] = df['volume'] > df['volume'].rolling(20).mean() # 爆量因子
            df['factor_pass'] = df['factor_pass'].fillna(False)
            
            # 模擬 AI 預測結果 (實戰中請替換為你的 LSTM 輸出)
            final_signals = np.random.choice([True, False], size=len(df), p=[0.3, 0.7]) 

            # 2. 轉換資料型態並丟入核心回測引擎
            test_dates = df['trade_date'].tolist()
            backtest_prices = df['close_price'].values
            ma20_data = df['ma20'].values
            factor_pass_data = df['factor_pass'].values

            # 呼叫你精心撰寫、帶有防呆機制的回測模組
            final_cap, eq_curve, trade_log, trade_profits = backtest_core.run_backtest(
                test_dates=test_dates,
                backtest_prices=backtest_prices,
                final_signals=final_signals,
                ma20_data=ma20_data,
                factor_pass_data=factor_pass_data,
                initial_capital=initial_capital,
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit
            )

            # 3. 結算綜合績效指標
            metrics = backtest_core.calculate_metrics(initial_capital, final_cap, eq_curve, trade_profits)

        # ==========================================
        # 📊 渲染前端儀表板 (Dashboard)
        # ==========================================
        
        # [區塊 A：核心績效指標 KPIs]
        st.subheader("📊 策略核心績效 (KPIs)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("總報酬率", f"{metrics['Total Return (%)']:.2f} %")
        col2.metric("勝率", f"{metrics['Win Rate (%)']:.2f} %")
        col3.metric("最大回撤 (MDD)", f"{metrics['Max Drawdown (%)']:.2f} %")
        col4.metric("夏普值 (Sharpe)", f"{metrics['Sharpe Ratio']:.2f}")

        # [區塊 B：Plotly 互動式資金曲線]
        st.markdown("---")
        st.subheader("💰 累積淨值走勢 (AI策略 vs 大盤買入持有)")
        
        cumulative_market = backtest_prices / backtest_prices[0]
        cumulative_strategy = np.array(eq_curve) / initial_capital

        fig = go.Figure()
        # 加入大盤基準線
        fig.add_trace(go.Scatter(x=test_dates, y=cumulative_market, mode='lines', name='Benchmark (大盤)', line=dict(color='gray', dash='dot')))
        # 加入 AI 策略淨值線
        fig.add_trace(go.Scatter(x=test_dates, y=cumulative_strategy, mode='lines', name='AI 雙因子策略', line=dict(color='#FFD700', width=2.5)))
        # 加入初始本金基準線
        fig.add_hline(y=1.0, line_dash="dash", line_color="white", opacity=0.3)
        
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(title="交易日期", showgrid=False), 
            yaxis=dict(title="累積報酬 (1.0 = 初始本金)", tickformat=".2f", gridcolor='rgba(255,255,255,0.1)'),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)
        # [區塊 C：AI 買賣點精準標記 (Trade Executions)]
        st.markdown("---")
        st.subheader("🎯 AI 買賣點精準標記 (Trade Executions)")

        fig_trades = go.Figure()

        # 1. 畫出真實股價底線
        fig_trades.add_trace(go.Scatter(
            x=test_dates, y=backtest_prices,
            mode='lines', name='實際收盤價',
            line=dict(color='cyan', width=1.5),
            opacity=0.6
        ))

        # 2. 解析交易日誌 (trade_log) 抓出買賣點
        buy_dates, buy_prices = [], []
        sell_dates, sell_prices = [], []

        for log in trade_log:
            # log 的格式是：(日期, 動作, 價格, 餘額, 股數)
            date, action, price, _, _ = log 
            if "BUY" in action:
                buy_dates.append(date)
                buy_prices.append(price)
            elif "SELL" in action or "STOP LOSS" in action or "TAKE PROFIT" in action:
                sell_dates.append(date)
                sell_prices.append(price)

        # 3. 標記買進點 (綠色向上三角形 ▲)
        fig_trades.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode='markers', name='買進 (BUY)',
            marker=dict(symbol='triangle-up', color='lime', size=12, line=dict(width=1, color='black'))
        ))

        # 4. 標記賣出點 (紅色向下三角形 ▼)
        fig_trades.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode='markers', name='賣出/停損利 (SELL)',
            marker=dict(symbol='triangle-down', color='red', size=12, line=dict(width=1, color='black'))
        ))

        # 設定圖表版面
        fig_trades.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(title="交易日期", showgrid=False), 
            yaxis=dict(title="真實股價 (元)", gridcolor='rgba(255,255,255,0.1)'),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig_trades, use_container_width=True)

        # [區塊 D：自動化交易日誌]
        st.markdown("---")
        st.subheader("📝 系統交易日誌 (Trade Log)")
        if trade_log:
            df_log = pd.DataFrame(trade_log, columns=["日期", "交易動作", "成交價格", "帳戶餘額", "變動股數"])
            # 將日期格式化，看起來更專業
            df_log['日期'] = pd.to_datetime(df_log['日期']).dt.strftime('%Y-%m-%d')
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("本次回測期間無任何交易發生。")

# 確保程式碼被直接執行時才啟動 (模組化設計標準)
if __name__ == "__main__":
    main()