import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine

# 1. 設定資料庫連線引擎
# 👉 記得換成你的密碼
db_url = "postgresql+psycopg2://postgres:john1207@localhost:5432/quant_db"
engine = create_engine(db_url)

print("⏳ 正在從 Yahoo Finance 抓取 AAPL 歷史股價...")

# 2. Extract (萃取)
ticker = 'AAPL'
df = yf.download(ticker, start='2023-01-01', end='2024-01-01')

# ----------------- 這裡是修復的關鍵區域 -----------------
# 3. Transform (轉換)

# 防護網一：如果 yfinance 回傳的是多層級欄位 (MultiIndex)，我們把它強制壓平
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)

# 將 Date 從 Index 變成一個獨立的欄位
df.reset_index(inplace=True)

# 統一將所有欄位名稱轉成字串，避免格式混亂
df.columns = [str(col).strip() for col in df.columns]

# 防護網二：如果 yfinance 這次沒給 'Adj Close'，我們就複製 'Close' 來頂替
if 'Adj Close' not in df.columns and 'Close' in df.columns:
    df['Adj Close'] = df['Close']

# 開始重新命名成資料庫格式
df = df.rename(columns={
    'Date': 'trade_date',
    'Open': 'open_price',
    'High': 'high_price',
    'Low': 'low_price',
    'Close': 'close_price',
    'Adj Close': 'adj_close',
    'Volume': 'volume'
})

# 新增我們自訂的主鍵欄位 ticker_symbol
df['ticker_symbol'] = ticker

# --------------------------------------------------------

# 篩選並排列出我們需要的欄位
final_df = df[['ticker_symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'adj_close', 'volume']]

print(f"✅ 資料清洗完成，共 {len(final_df)} 筆資料。準備寫入資料庫...")

# 4. Load (載入)
try:
    final_df.to_sql('market_data', engine, if_exists='append', index=False)
    print("🎉 成功！所有歷史股價已批次寫入 PostgreSQL 的 market_data 表中。")

except Exception as e:
    print(f"❌ 寫入失敗，錯誤原因：{e}")