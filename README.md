# 比特幣自動交易機器人 (BTC Auto-Trading Bot)

一個基於 MA20 均線策略的自動化加密貨幣交易系統，具備完整的風控機制、資料持久化、RESTful API 查詢介面，並已容器化部署於雲端環境 24 小時運行。

## 專案動機

本專案旨在練習後端系統設計的完整生命週期：從一支單純的策略腳本出發，逐步加入資料庫持久化、防呆機制、對外查詢介面，最終容器化並部署上雲，模擬真實世界後端服務從開發到上線的完整流程。

目前串接的是 **幣安測試網（Binance Testnet）**，所有交易皆使用虛擬資金，不涉及真實財務風險。

## 系統架構

```
┌─────────────────┐         ┌──────────────────┐
│  btc_monitor.py  │         │      api.py       │
│  (交易機器人主程式) │         │   (FastAPI 服務)   │
│                  │         │                    │
│  - 抓取K線/計算MA20 │         │  - GET /           │
│  - 策略判斷/下單    │         │  - GET /trades      │
│  - 風控/止損       │         │  - GET /status      │
│  - 持倉狀態還原     │         │  - GET /balance      │
└────────┬─────────┘         └─────────┬──────────┘
         │                             │
         │        兩個獨立的 Docker 容器      │
         │                             │
         └──────────────┬──────────────┘
                         │
                  ┌──────▼───────┐
                  │  PostgreSQL   │
                  │  (Supabase)   │
                  └───────────────┘
```

機器人主程式與查詢 API 是**兩個獨立運行的程序**，透過共用的 PostgreSQL 資料庫溝通，各自用 `docker-compose` 定義並同時啟動，部署於 AWS EC2 (Ubuntu) 上 24 小時運行。

## 技術棧

| 類別 | 技術 |
|---|---|
| 程式語言 | Python 3.14 |
| 交易所 API | python-binance (Binance Testnet) |
| Web 框架 | FastAPI + Uvicorn |
| 資料庫 | PostgreSQL (Supabase 代管) |
| 容器化 | Docker, Docker Compose |
| 雲端部署 | AWS EC2 (Ubuntu) |
| 通知 | Discord Webhook |

## 主要功能

### 交易機器人 (`btc_monitor.py`)
- **策略邏輯**：MA20（20 期移動平均線）交叉策略，價格突破 MA20 買入、跌破賣出
- **風控機制**：2% 硬性止損，觸發時優先於一般策略執行
- **API 防呆呼叫**：指數退避重試機制（`risk_manager.py`），應對網路暫時性故障
- **持倉持久化**：程式重啟時，自動查詢資料庫最後一筆交易紀錄，還原持倉狀態與進場價，避免因重啟導致誤判持倉、重複下單
- **即時通知**：交易觸發時，透過 Discord Webhook 即時推播

### 查詢 API (`api.py`)
- `GET /` — 服務健康檢查
- `GET /trades` — 查詢歷史交易紀錄（可帶 `limit` 參數）
- `GET /status` — 查詢目前持倉狀態（複用持倉還原邏輯）
- `GET /balance` — 即時查詢幣安測試網帳戶餘額

### 資料庫 (`db.py`)
- 交易紀錄持久化寫入 PostgreSQL
- 提供查詢介面供 `main.py`、`api.py` 共用

## 專案結構

```
btc-trading-bot/
├── btc_monitor.py       # 交易機器人主程式
├── api.py               # FastAPI 查詢服務
├── db.py                # 資料庫操作模組
├── risk_manager.py      # 風控與防呆重試邏輯
├── Dockerfile           # 機器人容器建置檔
├── Dockerfile.api        # API 容器建置檔
├── docker-compose.yml    # 雙容器編排設定
├── requirements.txt      # Python 套件依賴
└── .env                 # 環境變數（不納入版本控制）
```

## 本機執行

### 前置需求
- Python 3.11+
- Docker Desktop
- Supabase（或其他 PostgreSQL）資料庫
- 幣安測試網 API Key

### 環境變數設定
建立 `.env` 檔案：
```
BINANCE_API_KEY=你的幣安測試網API_KEY
BINANCE_SECRET_KEY=你的幣安測試網SECRET_KEY
DISCORD_WEBHOOK_URL=你的Discord_Webhook網址
DATABASE_URL=你的PostgreSQL連線字串
```

### 使用 Docker Compose 啟動
```bash
docker compose up --build -d
```

啟動後：
- 機器人開始運行，log 可透過 `docker compose logs -f` 查看
- API 服務於 `http://localhost:8000` 提供查詢，互動式文件位於 `http://localhost:8000/docs`

## 雲端部署

本專案已部署於 AWS EC2 (Ubuntu, t3.micro)，透過 `docker compose` 24 小時運行。部署過程中排查並解決了以下環境相容性問題：

1. **本機 Docker 容器 DNS 解析失敗**：排查發現為本機防毒軟體（McAfee）與 Docker Desktop 的 WSL2 網路架構相容性問題
2. **雲端環境資料庫連線失敗**：Supabase 預設的 Direct Connection 優先解析為 IPv6 位址，而 EC2 主機未開啟 IPv6 支援，改用 Supabase 提供的 **Session Pooler（IPv4）** 連線字串解決
3. **連線字串特殊字元編碼問題**：資料庫密碼含特殊符號時，未經 URL 編碼會導致連線字串解析錯誤，改以純英數字密碼避免此問題

## 已知限制與未來規劃

- 目前資料庫僅有單一 `trades` 表，交易紀錄與幣別資訊未拆分正規化，未來可拆分為獨立的幣別維度表
- `bot_logs` 表已建立但尚未串接寫入邏輯
- 尚未串接批次資料清洗與排程分析（規劃導入 Airflow，定期產出交易績效報表）
- 下單重試機制目前對所有 API 呼叫一視同仁，尚未區分冪等（查詢）與非冪等（下單）操作，實盤環境需另外處理重複下單風險

## 授權

本專案僅供學習與作品集展示用途，所有交易皆於幣安測試網（虛擬資金）執行。
