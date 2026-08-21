import os
import psycopg2
import logging
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """初始化資料庫：建立所需的數據表 Schema"""
    create_trades_table = """
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        side VARCHAR(10) NOT NULL,      -- BUY 或 SELL
        price NUMERIC(18, 8) NOT NULL,  -- 成交價格
        quantity NUMERIC(18, 8) NOT NULL, -- 數量
        pnl NUMERIC(18, 8) DEFAULT 0,    -- 損益 (僅賣出時記錄)
        executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_logs_table = """
    CREATE TABLE IF NOT EXISTS bot_logs (
        id SERIAL PRIMARY KEY,
        level VARCHAR(10) NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """

    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(create_trades_table)
                cursor.execute(create_logs_table)
        logging.info("✅ PostgreSQL 資料庫初始化成功，數據表建置完成！")
    except Exception as e:
        logging.error(f"❌ 資料庫初始化失敗: {e}")
    finally:
        if conn is not None:
            conn.close()

def record_trade(symbol, side, price, quantity, pnl=0.0):
    """寫入交易紀錄"""
    sql = """
    INSERT INTO trades (symbol, side, price, quantity, pnl)
    VALUES (%s, %s, %s, %s, %s);
    """
    conn = None
    try:
        clean_price = float(price)
        clean_quantity = float(quantity)
        clean_pnl = float(pnl)
        clean_side = str(side)
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (symbol, clean_side, clean_price, clean_quantity, clean_pnl))
        logging.info(f"💾 已同步交易紀錄至 PostgreSQL ({clean_side} {clean_quantity} {symbol} @ ${clean_price:.2f})")
    except Exception as e:
        logging.error(f"❌ 寫入交易紀錄失敗: {e}")
    finally:
        if conn is not None:
            conn.close()

def get_last_trade(symbol):
    """查詢最後一筆交易，用來還原啟動時的持倉狀態"""
    sql = """
    SELECT side, price, executed_at FROM trades
    WHERE symbol = %s
    ORDER BY id DESC LIMIT 1;
    """
    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (symbol,))
                row = cursor.fetchone()
        return row  # (side, price) 或 None（如果從沒交易過）
    except Exception as e:
        logging.error(f"❌ 查詢最後交易紀錄失敗: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()

def get_all_trades(limit=50):
    """查詢歷史交易紀錄，依時間新到舊排序"""
    sql = """
    SELECT id, symbol, side, price, quantity, pnl, executed_at
    FROM trades
    ORDER BY id DESC
    LIMIT %s;
    """
    conn = None
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()
        return rows
    except Exception as e:
        logging.error(f"❌ 查詢交易紀錄失敗: {e}")
        return []
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    # 直接執行本檔案，測試資料庫連線並進行初始化建表
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    print("⏳ 正在測試與 Supabase PostgreSQL 連線...")
    init_db()