import asyncio
import os
from dotenv import load_dotenv
from concurrent.futures import TimeoutError
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.stdout import StdOutCallbackHandler
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from datetime import datetime

# 載入 .env 環境變數
load_dotenv()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

# 設定回調管理器，用於顯示 Agent 的思考→動作→觀察流程
callback_manager = CallbackManager([StdOutCallbackHandler()])

async def mcp_client_lifecycle(server_url: str, user_input: str) -> str:
    """
    連線 MCP Server，載入工具，執行 Zero-Shot ReAct Agent，並清理連線。
    使用 run_coroutine_threadsafe 將工具呼叫 coroutine 排入主事件迴圈。
    """
    loop = asyncio.get_running_loop()
    sse_ctx = sse_client(server_url)
    session = None
    try:
        read_stream, write_stream = await sse_ctx.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        # 動態載入 MCP 工具
        tools = []
        info = await session.list_tools()
        for t in info.tools:
            name, desc = t.name, t.description
            # 取得參數名稱列表（假定工具定義中含 args 或 parameters 欄位）
            if hasattr(t, 'args') and t.args:
                param_names = [p.name for p in t.args]
            elif hasattr(t, 'parameters') and t.parameters:
                param_names = [p.name for p in t.parameters]
            else:
                param_names = []

            def make_tool(tool_name, param_names, tool_desc):
                def _tool(*args, **kwargs):
                    # 處理位置參數映射到命名參數
                    call_kwargs = {}
                    if args and not kwargs:
                        if len(args) == 1 and len(param_names) == 1:
                            call_kwargs = {param_names[0]: args[0]}
                        else:
                            call_kwargs = {param_names[i]: args[i] for i in range(min(len(args), len(param_names)))}
                    else:
                        call_kwargs = kwargs.copy() if kwargs else {}

                    # 修正：確保所有必填參數都在 call_kwargs 中
                    for pname in param_names:
                        if pname not in call_kwargs:
                            call_kwargs[pname] = None

                    future = asyncio.run_coroutine_threadsafe(
                        session.call_tool(tool_name, call_kwargs), loop
                    )
                    try:
                        res = future.result(timeout=30)
                    except TimeoutError:
                        raise RuntimeError(f"Tool call timeout: {tool_name}")
                    return res.content[0].text
                return _tool

            tools.append(Tool(name=name, func=make_tool(name, param_names, desc), description=desc))

        # 組建系統提示與 Agent
        tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        system_template = f"""
你是一個智慧助理。以下是你能呼叫的工具：
{tool_descriptions}

注意：如果使用者只是打招呼或進行簡單聊天，請直接用自然語言回答，不要呼叫任何工具。
特別提醒：若要呼叫 `google_calendar`，arguments 裡務必回傳以下格式：
特別提醒：呼叫 `google_calendar` 時，請依官方 API 參數填入對應欄位（ISO 8601 時間字串），並參考下例：

"tool_calls": [
  {{
    "name": "google_calendar",
    "arguments": {{
      "operation": "list_events",
      "time_min": "2025-07-18T00:00:00+08:00",
      "time_max": "2025-07-18T23:59:59+08:00"
    }}
  }},
  {{
    "name": "google_calendar",
    "arguments": {{
      "operation": "find_free_slots",
      "time_min": "2025-07-19T09:00:00+08:00",
      "time_max": "2025-07-19T17:00:00+08:00",
      "duration": 60
    }}
  }},
  {{
    "name": "google_calendar",
    "arguments": {{
      "operation": "add_event",
      "title": "專案會議",
      "start": "2025-07-20T14:00:00+08:00",
      "end": "2025-07-20T15:00:00+08:00",
      "description": "討論下階段開發"
    }}
  }},
  {{
    "name": "google_calendar",
    "arguments": {{
      "operation": "auto_schedule",
      "time_min": "2025-07-21T09:00:00+08:00",
      "time_max": "2025-07-21T18:00:00+08:00",
      "events": [{{"title":"撰寫報告","duration_min":120}},{{"title":"Code Review","duration_min":60}}]
    }}
  }}
]
當你需要以google_calendar以外的工具取得資料或執行動作時，請以 JSON 格式返回 tool_calls，格式如下：
{{{{ "tool_calls": null, "raw_response": <API 回傳的 JSON 物件> }}}}

城市名稱請用英文；日期請用 ISO 8601 格式；若不需呼叫工具，返回：

{{{{ "tool_calls": null }}}}
"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        llm = ChatOpenAI(
            model_name=OPENAI_MODEL_NAME,
            temperature=0.7,
            callback_manager=callback_manager,
            verbose=True
        )
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            prompt=prompt,
            memory=memory,
            verbose=True
        )

        result = await asyncio.to_thread(agent.run, user_input)
        return result

    finally:
        if session:
            try:
                await session.__aexit__(None, None, None)
            except:
                pass
        if sse_ctx:
            try:
                await sse_ctx.__aexit__(None, None, None)
            except:
                pass

async def main():
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:1234/sse")
    print(f"🔗 Connecting to MCP Server: {server_url}")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            print("拜拜！")
            break
        try:
            answer = await mcp_client_lifecycle(server_url, user_input)
            print("\n🎯 Agent 最終回覆:")
            print(answer)
        except Exception as e:
            print(f"執行過程發生錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(main())
