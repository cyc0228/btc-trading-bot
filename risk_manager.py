import time
import logging
from binance.exceptions import BinanceAPIException, BinanceRequestException

# 設定 Logging，紀錄重要事件
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


# 1. 網路重試機制（指數退避演算法）
def safe_api_call(func, *args, max_retries=5, initial_delay=2, **kwargs):
    """通用防呆呼叫函式：當 API 發生網路例外時，自動進行指數退避重試"""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (BinanceAPIException, BinanceRequestException, ConnectionError, TimeoutError) as e:
            logging.warning(f"⚠️ API 呼叫失敗 (第 {attempt}/{max_retries} 次嘗試): {e}")
            if attempt == max_retries:
                logging.error("❌ 已達最大重試次數，系統拋出例外。")
                raise e
            logging.info(f"⏳ 等待 {delay} 秒後重新嘗試...")
            time.sleep(delay)
            delay *= 2  # 次數翻倍 (例如: 2s -> 4s -> 8s -> 16s)

# 2. 2% 硬性止損判斷機制
def check_stop_loss(entry_price, current_price, stop_loss_pct=0.02):
    """檢查當前價格是否已觸發硬性止損 (預設 2%)"""
    if entry_price <= 0:
        return False
    
    # 計算當前跌幅
    price_change = (current_price - entry_price) / entry_price
    
    # 如果跌幅小於等於 -2% (-0.02)
    if price_change <= -stop_loss_pct:
        logging.critical(f"🚨 觸發 {stop_loss_pct*100}% 硬性止損！入場價: {entry_price}, 當前價: {current_price}, 虧損率: {price_change*100:.2f}%")
        return True
    return False

