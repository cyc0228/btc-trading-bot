import os
from fastapi import FastAPI
from dotenv import load_dotenv
from binance.client import Client
from db import get_all_trades, get_last_trade

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
SYMBOL = "BTCUSDT"

# api.py 是獨立程序，需要自己建立一份 Client 連線
client = Client(API_KEY, SECRET_KEY, testnet=True)

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "交易機器人 API 運作中"}

@app.get("/trades")
def read_trades(limit: int = 50):
    """查詢歷史交易紀錄"""
    rows = get_all_trades(limit)
    trades = []
    for row in rows:
        trades.append({
            "id": row[0],
            "symbol": row[1],
            "side": row[2],
            "price": float(row[3]),
            "quantity": float(row[4]),
            "pnl": float(row[5]),
            "executed_at": row[6].isoformat()
        })
    return {"count": len(trades), "trades": trades}

@app.get("/status")
def read_status():
    """查詢目前持倉狀態（依最後一筆交易判斷）"""
    last_trade = get_last_trade(SYMBOL)

    if last_trade is None:
        return {
            "symbol": SYMBOL,
            "position": False,
            "entry_price": 0.0,
            "message": "尚無交易紀錄"
        }

    side, price, executed_at = last_trade

    if side == "BUY":
        return {
            "symbol": SYMBOL,
            "position": True,
            "entry_price": float(price),
            "last_trade_at": executed_at.isoformat(),
            "message": "目前持有未平倉部位"
        }
    else:
        return {
            "symbol": SYMBOL,
            "position": False,
            "entry_price": 0.0,
            "last_trade_at": executed_at.isoformat(),
            "message": "目前無持倉"
        }

@app.get("/balance")
def read_balance():
    """查詢幣安測試網帳戶即時餘額"""
    try:
        account = client.get_account()
        balances = {}
        for asset in account["balances"]:
            if asset["asset"] in ["BTC", "USDT"]:
                balances[asset["asset"]] = float(asset["free"])
        return {"balances": balances}
    except Exception as e:
        return {"error": str(e)}