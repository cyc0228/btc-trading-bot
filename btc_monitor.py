import os
import time
import requests
import logging
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from db import init_db, record_trade, get_last_trade
from risk_manager import safe_api_call, check_stop_loss

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

# testnet=True 會自動把所有下單請求轉向幣安測試網伺服器
client = Client(API_KEY, SECRET_KEY, testnet=True)

SYMBOL = "BTCUSDT"
QUANTITY = 0.001
STOP_LOSS_PCT = 0.02

def send_discord(msg):
    """發送 Discord 訊息"""
    if DISCORD_WEBHOOK:
        data = {"content": msg}
        try:
            requests.post(DISCORD_WEBHOOK, json=data, timeout=5)
        except Exception as e:
            logging.error(f"Discord 發送失敗: {e}")

def get_klines():
    """抓取 K 線並計算 MA20 (用 safe_api_call 防呆) """
    klines = safe_api_call(
        client.get_klines,
        symbol=SYMBOL,
        interval=Client.KLINE_INTERVAL_1MINUTE,
        limit=30)
    df = pd.DataFrame(klines, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['ma20'] = df['close'].rolling(window=20).mean()
    return df

def execute_order(side):
    """執行測試網市價單 (用 safe_api_call 防呆) """
    try:
        order = safe_api_call(
            client.create_order,
            symbol=SYMBOL,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=QUANTITY)
        logging.info(f"✅ 測試網 {side} 成功！訂單 ID: {order['orderId']}")
        return True
    except Exception as e:
        logging.error(f"❌ 下單失敗: {e}")
        return False

# 驗證測試網連線 (用 safe_api_call 防呆)
try:
    account = safe_api_call(client.get_account)
    logging.info("--- 幣安測試網連線成功！---")
    for asset in account['balances']:
        if asset['asset'] in ['BTC', 'USDT']:
            logging.info(f"目前 {asset['asset']} 虛擬餘額: {asset['free']}")
    logging.info("----------------------------")
except Exception as e:
    logging.critical(f"無法連線至幣安測試網,請檢查API金鑰或網路連線: {e}")
    exit()

logging.info("🚀 V2.0 自動交易機器人 (防呆風控升級版) 啟動中...")

# 啟動時自動建立與檢查 PostgreSQL 資料表
init_db()

last_trade = get_last_trade(SYMBOL)
if last_trade and last_trade[0] == "BUY":
    position = True
    entry_price = float(last_trade[1])
    logging.info(f"🔄 偵測到未平倉部位，還原狀態：進場價 ${entry_price:.2f}")
else:
    position = False
    entry_price = 0.0
    logging.info("🔄 目前無未平倉部位，從無持倉狀態啟動")

while True:
    try:
        df = get_klines()
        latest = df.iloc[-1]
        price = latest['close']
        ma20 = latest['ma20']
        
        logging.info(f"當前價: ${price:.2f} | MA20: ${ma20:.2f} | 持倉: {position}")

        # 1. 優先風控：若有持倉，優先檢查是否觸發 2% 硬性止損
        if position:
            if check_stop_loss(entry_price, price, stop_loss_pct=STOP_LOSS_PCT):
                logging.critical(f"🚨 觸發 {STOP_LOSS_PCT * 100}% 硬性止損！進場價: ${entry_price:.2f} | 當前價: ${price:.2f}")
                if execute_order(Client.SIDE_SELL):
                    pnl = (price - entry_price) * QUANTITY
                    # 止損賣出成功：同步寫入 Supabase 資料庫
                    record_trade(symbol=SYMBOL, side="SELL", price=price, quantity=QUANTITY, pnl=pnl)

                    position = False
                    send_discord(f"🚨 **硬性止損觸發平倉** | 價格: ${price:.2f} | 原成本: ${entry_price:.2f}")
                    entry_price = 0.0
                time.sleep(10)
                continue

        # 2. MA20 均線策略判斷
        # 買入邏輯：價格突破 MA20 且 目前無持倉
        if price > ma20 and not position:
            logging.info("🟢 觸發買入訊號，正在向測試網下單...")
            if execute_order(Client.SIDE_BUY):
                # 買入成功：同步寫入 Supabase 資料庫
                record_trade(symbol=SYMBOL, side="BUY", price=float(price), quantity=float(QUANTITY), pnl=0.0)

                position = True
                entry_price = price
                send_discord(f"🚀 **V2.0 自動買入** | 價格: ${price:.2f} | 數量: {QUANTITY} BTC")

        # 賣出邏輯：價格跌破 MA20 且 目前有持倉
        elif price < ma20 and position:
            logging.info("🔴 觸發賣出訊號，正在向測試網下單...")
            if execute_order(Client.SIDE_SELL):
                pnl = (price - entry_price) * QUANTITY
                # 策略賣出成功：同步寫入 Supabase 資料庫
                record_trade(symbol=SYMBOL, side="SELL", price=float(price), quantity=float(QUANTITY), pnl=float(pnl))

                position = False
                entry_price = 0.0
                send_discord(f"🔻 **V2.0 自動賣出** | 價格: ${price:.2f} | 數量: {QUANTITY} BTC")

    except Exception as e:
        logging.error(f"執行時發生錯誤: {e}")

    time.sleep(10)