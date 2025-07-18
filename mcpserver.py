import asyncio
import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.exceptions import DefaultCredentialsError, MalformedError
from datetime import datetime, timedelta
#from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from datetime import datetime
from typing import Optional

load_dotenv()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")


# 設定金鑰與常數
SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "gen-lang-client-0938626238-7558a5e0b177.json"
)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
EXCHANGE_RATE_API_KEY = "8cb1aa5e37c5bfe77015eb6c"
NEWS_API_KEY = "f3e2604664344a1fb322b220f79c8a3f"

# Google Calendar 服務初始化
#credentials = service_account.Credentials.from_service_account_file(
#    SERVICE_ACCOUNT_FILE, scopes=SCOPES
#)
#calendar_service = build("calendar", "v3", credentials=credentials)

try:
    if not os.path.isfile(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"找不到服務帳戶憑證檔: {SERVICE_ACCOUNT_FILE}")
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    calendar_service = build("calendar", "v3", credentials=credentials)
except (FileNotFoundError, DefaultCredentialsError, MalformedError) as e:
    print(f"❌ 載入 Google Calendar 服務帳戶憑證失敗: {e}")
    print("請確認已下載並提供正確的 Service Account JSON，並且包含 'client_email' 與 'token_uri' 欄位。")
    print("可設定環境變數: export GOOGLE_APPLICATION_CREDENTIALS=<path-to-json>")
    raise SystemExit(1)

# 初始化 MCP Server
mcp = FastMCP(name="demo-server", host="0.0.0.0", port=1234)

@mcp.tool(
    name="get_weather",
    description="獲取指定城市的天氣資訊，參數: city (str)"
)
async def get_weather(city: str) -> str:
    try:
        API_KEY = "8e3eab06a16bd71632cffc55330c6c12"
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": API_KEY, "units": "metric", "lang": "zh_tw"}
        )
        data = resp.json()
        if resp.status_code == 200:
            desc = data['weather'][0]['description']
            temp = data['main']['temp']
            return f"{city} 天氣：{desc}，溫度：{temp}°C"
        return f"無法取得天氣資料：{data.get('message', '未知錯誤')}"
    except Exception as e:
        return f"天氣 API 調用失敗：{e}"

@mcp.tool(
    name="convert_currency",
    description=(
        "貨幣兌換工具：可將指定金額從一種貨幣轉換為另一種貨幣。"
        "適用於旅遊、購物、財務規劃等情境，例如："
        "出國前查詢匯率、計算外幣消費金額、比較不同貨幣之間的價值。"
        "參數: amount (float, 欲兌換金額), from_currency (str, 原始貨幣代碼), to_currency (str, 目標貨幣代碼)。"
        "例如：convert_currency(100, 'USD', 'TWD') 可查詢 100 美元換算成新台幣的金額。"
    )
)
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/{from_currency.upper()}"
        resp = requests.get(url)
        data = resp.json()
        if resp.status_code == 200 and data.get("result") == "success":
            rates = data.get("conversion_rates", {})
            rate = rates.get(to_currency.upper())
            if rate:
                converted = amount * rate
                return f"{amount} {from_currency.upper()} = {converted:.2f} {to_currency.upper()} (匯率: {rate})"
            return f"無法找到目標貨幣 {to_currency.upper()} 的匯率資料"
        return f"匯率 API 錯誤：{data.get('error-type', data)}"
    except Exception as e:
        return f"匯率 API 調用失敗：{e}"

@mcp.tool(name="get_news_headlines", description="取得指定國家前 3 條新聞標題，參數: country (str)")
async def get_news_headlines(country: str) -> str:
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {"country": country.lower(), "pageSize": 3, "apiKey": NEWS_API_KEY, "language": "zh"}
        resp = requests.get(url, params=params)
        data = resp.json()
        if resp.status_code == 200 and data.get("status") == "ok":
            articles = data.get("articles", [])[:3]
            if not articles:
                return f"在 {country} 找不到新聞。"
            headlines = [f"{idx+1}. {art.get('title')}" for idx, art in enumerate(articles)]
            return "\n".join(headlines)
        return f"新聞 API 錯誤：{data.get('message', data)}"
    except Exception as e:
        return f"新聞 API 調用失敗：{e}"

@mcp.tool(name="suggest_activity", description="根據天氣建議適合的活動，參數: context (str)")
async def suggest_activity(context: str) -> str:
    cond = context.lower()
    if "晴" in cond or "sunny" in cond:
        return "天氣晴朗，建議你去戶外散步或運動。"
    if "雨" in cond or "rain" in cond:
        return "下雨天，推薦你在室內閱讀或看電影。"
    return "建議活動：根據當前情況，可自由決定。"

@mcp.tool(name="get_time", description="取得現在時間，參數: 無")
async def get_time() -> str:
    try:
        now = datetime.now()
        weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        weekday_str = weekday_map[now.weekday()]
        return f"現在時間（系統時間）：{now.strftime('%Y-%m-%d %H:%M:%S')}，{weekday_str}"
    except Exception as e:
        return f"取得現在時間失敗：{e}"

@mcp.tool(
    name="google_calendar",
    description="Google Calendar 多功能：操作(list_events, find_free_slots, add_event, auto_schedule)。參數: operation (str, 必填: list_events/find_free_slots/add_event/auto_schedule)、time_min (str, ISO8601)、time_max (str, ISO8601)、duration (int, 分鐘)、title (str)、start (str, ISO8601)、end (str, ISO8601)、description (str)、timezone (str, 預設 Asia/Taipei)、events (list)、date (str, ISO8601)"
)
async def google_calendar(
    operation: str,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    duration: Optional[int] = None,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: str = "",
    timezone: str = "Asia/Taipei",
    events: Optional[list] = None,
    date: Optional[str] = None  # 新增 date 參數
) -> str:
    # 檢查必填參數
    missing_args = []
    if operation is None:
        missing_args.append("operation")
    # 依據 operation 檢查其他必填參數
    op = (operation or "").lower()
    if op == "find_free_slots":
        if not time_min:
            missing_args.append("time_min")
        if not time_max:
            missing_args.append("time_max")
        if duration is None:
            missing_args.append("duration")
    if op == "list_events":
        if not time_min:
            missing_args.append("time_min")
        if not time_max:
            missing_args.append("time_max")
    if op == "add_event":
        if not title:
            missing_args.append("title")
        if not start:
            missing_args.append("start")
        if not end:
            missing_args.append("end")
    if op == "auto_schedule":
        if not time_min:
            missing_args.append("time_min")
        if not time_max:
            missing_args.append("time_max")
        if not events:
            missing_args.append("events")
    if missing_args:
        print(f"[google_calendar] 缺少必填參數: {', '.join(missing_args)}")
        print(f"❌ 缺少必填參數: {', '.join(missing_args)}")
        return f"❌ 缺少必填參數: {', '.join(missing_args)}"

    try:
        # 若有 date 參數且 time_min/time_max 未指定，則自動設為該日期的全天
        if date and (not time_min or not time_max):
            try:
                dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                time_min = dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                time_max = (dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()
                print(f"自動設定 time_min: {time_min}, time_max: {time_max} 以符合日期 {date}")
            except Exception as e:
                return f"日期格式錯誤: {e}"

        if op == "list_events":
            if not time_min or not time_max:
                return "list_events 操作需要參數: time_min (str, ISO8601), time_max (str, ISO8601)。"
            events_result = calendar_service.events().list(
                calendarId='primary', timeMin=time_min,
                timeMax=time_max, singleEvents=True, orderBy='startTime'
            ).execute()
            items = events_result.get('items', [])
            if not items:
                return "此期間無事件。"
            return "\n".join(
                f"- {evt['start'].get('dateTime', evt['start'].get('date'))}: {evt.get('summary','')}" 
                for evt in items
            )

        if op == "find_free_slots":
            if not time_min or not time_max or duration is None:
                return "find_free_slots 操作需要參數: time_min (str, ISO8601), time_max (str, ISO8601), duration (int, 分鐘)。"
            body = {"timeMin": time_min, "timeMax": time_max, "timeZone": timezone, "items":[{"id":"primary"}]}
            fb = calendar_service.freebusy().query(body=body).execute()
            busy = fb['calendars']['primary']['busy']
            cursor = datetime.fromisoformat(time_min)
            end_limit = datetime.fromisoformat(time_max)
            slots = []
            for b in busy:
                st = datetime.fromisoformat(b['start'])
                if (st - cursor).total_seconds() >= duration*60:
                    slots.append((cursor.isoformat(), st.isoformat()))
                cursor = max(cursor, datetime.fromisoformat(b['end']))
            if (end_limit - cursor).total_seconds() >= duration*60:
                slots.append((cursor.isoformat(), end_limit.isoformat()))
            if not slots:
                return "無符合條件之空閒時段。"
            return "\n".join(f"空閒: {s[0]} 至 {s[1]}" for s in slots)

        if op == "add_event":
            if not title or not start or not end:
                return "add_event 操作需要參數: title (str), start (str, ISO8601), end (str, ISO8601)。"
            event = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start, "timeZone": timezone},
                "end": {"dateTime": end, "timeZone": timezone},
            }
            created = calendar_service.events().insert(calendarId='primary', body=event).execute()
            return f"已建立事件: {created.get('htmlLink')}"

        if op == "auto_schedule":
            if not time_min or not time_max or not events:
                return "auto_schedule 操作需要參數: time_min (str, ISO8601), time_max (str, ISO8601), events (list)。"
            fb_body = {"timeMin": time_min, "timeMax": time_max, "timeZone": timezone, "items":[{"id":"primary"}]}
            fb = calendar_service.freebusy().query(body=fb_body).execute()
            busy = fb['calendars']['primary']['busy']
            cursor = datetime.fromisoformat(time_min)
            schedule = []
            for e in events or []:
                dur = timedelta(minutes=e.get('duration_min', 60))
                for b in busy:
                    bstart = datetime.fromisoformat(b['start'])
                    if bstart - cursor >= dur:
                        break
                    cursor = max(cursor, datetime.fromisoformat(b['end']))
                st = cursor
                ed = cursor + dur
                calendar_service.events().insert(
                    calendarId='primary',
                    body={
                        'summary': e['title'],
                        'start': {'dateTime': st.isoformat(), 'timeZone': timezone},
                        'end': {'dateTime': ed.isoformat(), 'timeZone': timezone}
                    }
                ).execute()
                schedule.append(f"{e['title']}: {st.isoformat()} - {ed.isoformat()}")
                cursor = ed
            return "已自動排程:\n" + "\n".join(schedule)

        return f"未知操作: {operation}"
    except Exception as e:
        return f"Google Calendar 操作失敗: {e}"
      
@mcp.tool(name="get_global_attractions", description="全球景點查找工具，參數: country (str), budget (float), days (int)")
async def get_global_attractions(country: str, budget: float, days: int) -> str:
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
    if not GOOGLE_PLACES_API_KEY:
        return "請設定 GOOGLE_PLACES_API_KEY 環境變數。"
    # 呼叫 Google Places Text Search
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': f'tourist attractions in {country}',
        'key': GOOGLE_PLACES_API_KEY,
        'language': 'zh-TW'
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if data.get('status') != 'OK':
        return f"Places API 錯誤：{data.get('status')}"
    results = data.get('results', [])
    per_day = max(1, len(results) // days)
    itinerary = []
    for i in range(days):
        day_attractions = results[i*per_day:(i+1)*per_day]
        names = [attr.get('name') for attr in day_attractions]
        budget_half = budget / days
        itinerary.append(f"Day {i+1} (預算 {budget_half:.2f} USD): "+ ", ".join(names))
    return "\n".join(itinerary)

async def main():
    print("✅ 啟動 MCP Server (SSE) → http://127.0.0.1:1234/sse")
    await mcp.run_sse_async()

if __name__ == "__main__":
    asyncio.run(main())
