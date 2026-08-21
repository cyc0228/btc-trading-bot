import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()
client = Client(os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY"), testnet=True)

account = client.get_account()
for asset in account['balances']:
    if asset['asset'] in ['BTC', 'USDT']:
        print(f"💰 目前 {asset['asset']} 餘額: {asset['free']}")