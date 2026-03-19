import os
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==========================================
# 🛡️ 環境變數與資料庫連線設定 (資安保護)
# ==========================================
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

def load_and_preprocess_data(ticker, start_date, end_date):
    """
    智慧型資料載入器 (支援 ETL 增量更新 Incremental Load)
    """
    try:
        # 1. 建立安全的資料庫連線
        db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(db_url)
        
        # 2. 先去資料庫查詢現有的資料
        sql_query = f"""
            SELECT 
                trade_date AS "Date", open_price AS "Open", high_price AS "High",
                low_price AS "Low", close_price AS "Close", volume AS "Volume"
            FROM market_data 
            WHERE ticker_symbol = '{ticker}' 
              AND trade_date >= '{start_date}' 
              AND trade_date <= '{end_date}'
            ORDER BY trade_date ASC;
        """
        df = pd.read_sql_query(sql_query, engine)
        
        # 3. 🌟 核心進化：增量更新邏輯 (Incremental Load) 🌟
        need_fetch = False
        fetch_start_date = start_date

        if df.empty:
            print(f"⚠️ 資料庫完全沒有 {ticker} 的資料，準備進行全量抓取...")
            need_fetch = True
        else:
            # 檢查資料庫裡面的「最新日期」
            latest_db_date = pd.to_datetime(df['Date'].max()).strftime('%Y-%m-%d')
            
            # 如果資料庫的最新日期，小於我們要求的 end_date，代表資料過期了！
            if latest_db_date < end_date:
                print(f"⚠️ 發現資料過期！資料庫最新報價停留在 {latest_db_date}，啟動自動爬蟲...")
                # 將爬蟲的起點設定為資料庫最新日期的「隔天」
                fetch_start_date = (pd.to_datetime(latest_db_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                need_fetch = True

        # 4. 啟動 yfinance 爬蟲補齊缺漏的資料
        if need_fetch:
            print(f"🌐 正在從 yfinance 抓取 {fetch_start_date} 到 {end_date} 的資料...")
            raw_df = yf.download(ticker, start=fetch_start_date, end=end_date)
            
            if not raw_df.empty:
                # --- 清洗與轉換流程 ---
                if isinstance(raw_df.columns, pd.MultiIndex):
                    raw_df.columns = raw_df.columns.droplevel(1)
                raw_df.reset_index(inplace=True)
                raw_df.columns = [str(col).strip() for col in raw_df.columns]
                
                if 'Adj Close' not in raw_df.columns and 'Close' in raw_df.columns:
                    raw_df['Adj Close'] = raw_df['Close']
                    
                db_df = raw_df.rename(columns={
                    'Date': 'trade_date', 'Open': 'open_price', 'High': 'high_price',
                    'Low': 'low_price', 'Close': 'close_price', 'Adj Close': 'adj_close', 'Volume': 'volume'
                })
                db_df['ticker_symbol'] = ticker
                db_df = db_df[['ticker_symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'adj_close', 'volume']]
                
                # --- 更新 Securities 表 ---
                stock_info = yf.Ticker(ticker).info
                company_name = stock_info.get('shortName', 'Unknown')
                sector = stock_info.get('sector', 'Unknown')
                
                with engine.connect() as conn:
                    sql_statement = text("""
                        INSERT INTO Securities (ticker_symbol, company_name, sector) 
                        VALUES (:ticker, :company, :sector) 
                        ON CONFLICT (ticker_symbol) DO NOTHING;
                    """)
                    conn.execute(sql_statement, {
                        "ticker": ticker, 
                        "company": company_name, 
                        "sector": sector
                    })
                    conn.commit()
                
                # --- 將新資料批次寫入 PostgreSQL ---
                db_df.to_sql('market_data', engine, if_exists='append', index=False)
                print(f"✅ 成功將 {len(db_df)} 筆最新市場資料自動寫入 PostgreSQL！")
                
                # 🌟 寫入完畢後，重新執行一次查詢，確保我們拿到包含剛剛寫入的最新大表
                df = pd.read_sql_query(sql_query, engine)
            else:
                print(f"ℹ️ API 回傳空值，可能這段期間沒有交易日 (例如週末或國定假日)。")

        # 若爬完還是空的 (可能防呆或下市)
        if df.empty:
            print(f"❌ 無法取得任何資料，請檢查股票代號。")
            return None

        # 5. 特徵工程與指標計算
        df.set_index('Date', inplace=True)
        df.index = pd.to_datetime(df.index)
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
        df['Factor_Pass'] = (df['Close'] > df['MA20']) & (df['Volume'] > df['Vol_MA20'])
        
        df['Return'] = df['Close'].pct_change()
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50) 
        
        df.dropna(inplace=True)

        return df

    except Exception as e:
        print(f"資料庫讀取或寫入發生錯誤：{e}")
        return None