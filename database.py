import psycopg2
import pandas as pd

# 1. 設定資料庫連線資訊 (就像一把鑰匙)
DB_CONFIG = {
    "dbname": "quant_db",
    "user": "postgres",
    "password": "john1207",  # 👉 請把這裡換成你剛剛安裝時設定的密碼
    "host": "localhost",
    "port": "5432"
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 只要這一行！呼叫我們剛剛寫在資料庫裡的 Procedure (CALL ExecuteTrade)
    # 參數依序是：user_id, ticker, action, price, quantity
    # 這次我們試著「賣出」500 股的 AAPL，假設賣出價 175.00
    cursor.execute("CALL ExecuteTrade(1, 'AAPL', 'SELL', 175.00, 500);")
    
    # 提交執行結果
    conn.commit()
    print("✅ 呼叫預存程序成功！已完成賣出交易。")

    # 驗收餘額 (原本買 AAPL 花了 170,000 剩 830,000。現在賣掉 500 股賺回 87,500，應該會變 917,500)
    cursor.execute("SELECT current_balance FROM Users WHERE user_id = 1;")
    new_balance = cursor.fetchone()[0]
    print(f"🏦 目前帳戶剩餘資金：{new_balance} 元")

except Exception as e:
    if 'conn' in locals():
        conn.rollback()
    print(f"❌ 交易失敗，錯誤原因：{e}")

finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()