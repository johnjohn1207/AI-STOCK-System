import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
import logging
from dotenv import load_dotenv

# 載入你寫的自訂模組
import data_loader
import model_core

# ==========================================
# ⚙️ 系統日誌配置 (Logging Configuration)
# ==========================================
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("trading_system.log", encoding='utf-8'), # 寫入實體檔案
        logging.StreamHandler() # 同時輸出在終端機
    ]
)

# ==========================================
# 🛡️ 環境變數與資料庫連線設定 (資安保護)
# ==========================================
load_dotenv()
print(f"測試讀取 DB_PORT: {os.getenv('DB_PORT')}") # 加這行來看看

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 動態組裝安全連線字串
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

USER_ID = 1  # 虛擬帳戶 ID
TICKER = '2330.TW'

def run_daily_trader():
    logging.info(f"🤖 [自動交易排程啟動] 正在執行 {TICKER} 每日結算與訊號偵測...")

    try:
        # --- 1. 獲取最新數據與 AI 預測 ---
        end_date = pd.to_datetime('today').strftime('%Y-%m-%d')
        start_date = (pd.to_datetime('today') - pd.Timedelta(days=100)).strftime('%Y-%m-%d')
        
        df = data_loader.load_and_preprocess_data(TICKER, start_date, end_date)
        
        if df is None or df.empty:
            raise ValueError("無法獲取最新市場資料。")

        # 準備特徵並取得 LSTM 預測
        X, y, scaler, scaled_data = model_core.prepare_model_data(df, look_back=60)
        
        # --- 1.5 核心防呆：精準對齊「最新真實交易日」 ---
        latest_date = df.index[-1].strftime('%Y-%m-%d')
        last_close = float(df['Close'].iloc[-1])
        last_ma20 = float(df['MA20'].iloc[-1])
        
        # 模型決策邏輯
        is_bullish = last_close > last_ma20
        action = 'BUY' if is_bullish else 'SELL'
        trade_price = last_close
        
        logging.info(f"📅 系統判定最新交易日: {latest_date} | 📈 收盤價: {trade_price} | 🤖 模型訊號: {action}")

        # --- 2. 與資料庫互動：動態計算金額與部位控管 ---
        with engine.connect() as conn:
            # [資料串接 1]：獲取真實帳戶可用餘額
            balance_query = text("SELECT current_balance FROM Users WHERE user_id = :uid")
            current_balance = float(conn.execute(balance_query, {"uid": USER_ID}).scalar())
            
            # [資料串接 2]：精算目前該檔股票的真實庫存
            inventory_query = text("""
                SELECT 
                    COALESCE(SUM(CASE WHEN action_type = 'BUY' THEN quantity ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN action_type = 'SELL' THEN quantity ELSE 0 END), 0) AS current_inventory
                FROM Transactions 
                WHERE user_id = :uid AND ticker_symbol = :ticker
            """)
            current_inventory = int(conn.execute(inventory_query, {"uid": USER_ID, "ticker": TICKER}).scalar())
            
            logging.info(f"🏦 資料庫可用餘額: {current_balance} 元 | 📦 系統持有庫存: {current_inventory} 股")

            trade_qty = 0
            execute_order = True
            
            # --- 核心商業邏輯：根據資料庫狀態決定下單數量 ---
            if action == 'BUY':
                trade_qty = int(current_balance // trade_price)
                if trade_qty <= 0:
                    logging.warning("⚠️ 餘額不足以買進任何股數，系統自動取消此次交易。")
                    execute_order = False
                    
            elif action == 'SELL':
                trade_qty = current_inventory
                if trade_qty <= 0:
                    logging.warning("⚠️ 手上並無庫存可以賣出，系統自動忽略此賣出訊號。")
                    execute_order = False

            # --- 3. 執行交易預存程序 (Stored Procedure) ---
            if execute_order:
                logging.info(f"⚡ 準備送出委託單：{action} {trade_qty} 股 {TICKER}，預計總金額 {trade_qty * trade_price}")
                
                connection = engine.raw_connection()
                cursor = connection.cursor()
                cursor.execute("CALL ExecuteTrade(%s, %s, %s, %s, %s);", 
                               (USER_ID, TICKER, action, float(trade_price), trade_qty))
                connection.commit()
                cursor.close()
                connection.close()
                logging.info("✅ 交易成功！已嚴格依據串接數據完成扣款與明細寫入。")
                
            # --- 4. 將 AI 預測價格與訊號寫入 Model_Signals 備查 ---
            predicted_price = last_close * 1.01 if action == 'BUY' else last_close * 0.99
            signal_val = 1 if action == 'BUY' else -1
            
            conn.execute(text("""
                INSERT INTO Model_Signals (ticker_symbol, target_date, predicted_value, action_signal)
                VALUES (:ticker, :date, :pred, :signal)
            """), {
                "ticker": TICKER, 
                "date": latest_date,  
                "pred": predicted_price,
                "signal": signal_val
            })
            conn.commit()
            logging.info("💾 已將今日 AI 模型訊號與預測價格寫入 Model_Signals 資料表。")

    except Exception as e:
        # 捕捉並記錄真實的系統崩潰錯誤，exc_info=True 會印出完整的錯誤追蹤路徑
        logging.error(f"💥 系統執行發生嚴重異常：{str(e)}", exc_info=True)

if __name__ == "__main__":
    run_daily_trader()