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

# ---------------------------------------------------------
# 3. 整合進主迴圈的示範邏輯
# # ---------------------------------------------------------
# if __name__ == "__main__":
#     # 模擬變數
#     position = True
#     entry_price = 65000.0  # 買入價格
    
#     print("=== 開始執行模組一：防呆與止損測試 ===")

#     # 模擬 1: 使用 safe_api_call 安全取得價格 (以 safe_api_call 包裹 Client 呼叫)
#     # current_price = safe_api_call(client.get_symbol_ticker, symbol="BTCUSDT")['price']
    
#     # 模擬 2: 價格下跌測試止損 (假設價格跌到 63500，跌幅 2.3%)
#     test_current_price = 63500.0 
    
#     if position:
#         is_triggered = check_stop_loss(entry_price, test_current_price, stop_loss_pct=0.02)
#         if is_triggered:
#             print(">>> 執行強制平倉處置！(發送市價賣出單)")
#             # safe_api_call(client.order_market_sell, symbol="BTCUSDT", quantity=0.001)
#             position = False

# utils.py 前面放 safe_api_call 和 check_stop_loss 的定義...

# ---------------------------------------------------------
# 獨立測試區塊 (只有執行 python utils.py 時才會跑)
# ---------------------------------------------------------
# if __name__ == "__main__":
#     print("🧪 === 開始獨立測試 utils.py 模組 ===")

#     # 1. 測試止損邏輯 (check_stop_loss)
#     print("\n[測試 1: 止損判斷]")
#     entry_price = 65000.0  # 買入價
    
#     # 情況 A: 價格只跌 1% (64350) -> 不應該觸發止損
#     price_normal = 64350.0
#     result_a = check_stop_loss(entry_price, price_normal, stop_loss_pct=0.02)
#     print(f"當前價 {price_normal} (跌 1%): 觸發止損 = {result_a} (預期: False)")

#     # 情況 B: 價格暴跌 2.5% (63375) -> 必須觸發止損
#     price_drop = 63375.0
#     result_b = check_stop_loss(entry_price, price_drop, stop_loss_pct=0.02)
#     print(f"當前價 {price_drop} (跌 2.5%): 觸發止損 = {result_b} (預期: True)")

#     # 2. 測試 safe_api_call 指數退避重試
#     print("\n[測試 2: 重試機制 (模擬失敗函式)]")
    
#     # 寫一個故意每次呼叫都報錯的假函式
#     def fake_failed_api():
#         print(" -> 模擬 API 斷線中...")
#         raise ConnectionError("網路連線逾時！")

#     try:
#         # 測試重試 3 次，每次延遲 1 秒 (1s -> 2s)
#         safe_api_call(fake_failed_api, max_retries=3, initial_delay=1)
#     except Exception as e:
#         print(f"最終結果: 順利捕獲例外，程式沒有慘死，最終訊息: {e}")

#     print("\n✅ === utils.py 獨立測試完成 ===")