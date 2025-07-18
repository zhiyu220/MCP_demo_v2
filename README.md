# MCP Demo Server 與 Zero-Shot ReAct Agent

本專案包含兩個主要元件：

* **`mcpserver.py`**：基於 Flask 的 API 伺服器，整合多個第三方服務（新聞、天氣、貨幣轉換、Google 地點搜尋）。
* **`zero_shot_react_demo.py`**：Zero-Shot ReAct Agent 示範，展示如何透過 LLM 操作工具呼叫（包含 `google_calendar`）。

---

## 功能特色

* **新聞擷取**：依國家別取得前三筆最新頭條新聞。
* **天氣查詢**：根據城市名稱取得當前天氣描述與溫度。
* **貨幣轉換**：將指定金額從一種貨幣兌換為另一種貨幣。
* **Google 地點搜尋**：依關鍵字與位置搜尋附近餐廳等地點。
* **Zero-Shot ReAct**：示範如何以自然語言驅動 LLM 自行決策並呼叫工具，例如查詢日曆、建立行事曆事件。

## 環境需求

* Python 3.8 以上
* Flask
* `requests`
* 第三方服務 API 金鑰：

  * `NEWS_API_KEY`
  * `OPENWEATHER_API_KEY`
  * `EXCHANGE_RATE_API_KEY`
  * `GOOGLE_PLACES_API_KEY`
  * （如需 Google Calendar，請設定 `GOOGLE_CALENDAR_CREDENTIALS`）

## 安裝步驟

1. 建立並啟用虛擬環境：

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
2. 安裝相依套件：

   ```bash
   pip install -r requirements.txt
   ```
3. 設定環境變數（範例）：

   ```bash
   export NEWS_API_KEY="your_news_api_key"
   export OPENWEATHER_API_KEY="your_openweather_api_key"
   export EXCHANGE_RATE_API_KEY="your_exchange_rate_api_key"
   export GOOGLE_PLACES_API_KEY="your_google_places_api_key"
   # 如需使用 Google Calendar
   export GOOGLE_CALENDAR_CREDENTIALS="path/to/credentials.json"
   ```

## 使用範例

1. 啟動伺服器：

   ```bash
   python mcpserver.py
   ```
2. 範例請求（新聞）：

   ```bash
   curl "http://localhost:5000/news?country=tw"
   ```
3. Zero-Shot ReAct Agent 執行：

   ```bash
   python zero_shot_react_demo.py
   ```

## 專案結構

```
.
├── mcpserver.py
├── zero_shot_react_demo.py
├── requirements.txt
├── YOUR_GOOGLE_CALANDER_SERVICE.json
├── .env
└── README.md
```
