"""AI 호스트 - 도구 명세가 모델의 선택을 어떻게 가르는지 관찰합니다. (완성 제공)

호스트 코드는 섹션 1 실습 2와 동일합니다. 이번 실습의 변수는 host.py가 아니라
server.py의 도구 명세(이름·description)입니다. 같은 동작을 하는 두 도구 중
모델이 어느 쪽을 고르는지를, 명세만 바꿔 가며 관찰하세요.

  process(query)        : 모호한 명세
  search_memos(keyword) : 구체적 명세 (같은 동작)
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport
from openai import OpenAI

load_dotenv()

MODEL = "openai/gpt-5.4"

# 모두 '메모 검색'을 의도한 요청입니다. 모델이 process와 search_memos 중 무엇을 고르는지 보세요.
USER_REQUESTS = [
    "회의 관련 메모를 찾아줘.",
    "커피라는 단어가 들어간 메모 있어?",
    "독서 관련해서 적어둔 거 검색해 줘.",
]


def to_llm_tools(mcp_tools):
    """MCP 도구 명세를 LLM이 이해하는 형식으로 변환합니다.

    함수 이름 -> name / docstring -> description / 타입 힌트 -> inputSchema.
    모델이 도구에 대해 아는 것은 이 세 가지뿐입니다.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


async def process_request(llm, mcp_client, llm_tools, user_request):
    """자연어 요청 하나를 처리하며 모델이 어떤 도구를 고르는지 출력합니다."""
    print(f"\n{'=' * 60}")
    print(f"사용자 요청    : {user_request}")

    messages = [
        {
            "role": "system",
            "content": "당신은 메모를 관리하는 AI 비서입니다. "
            "도구로 처리할 수 있는 요청은 반드시 제공된 도구를 사용하세요.",
        },
        {"role": "user", "content": user_request},
    ]

    response = llm.chat.completions.create(
        model=MODEL, messages=messages, tools=llm_tools
    )
    message = response.choices[0].message

    if not message.tool_calls:
        print("모델의 선택    : (도구 사용 안 함)")
        print(f"최종 답변     : {message.content}")
        return

    messages.append(message.model_dump(exclude_none=True))
    for tool_call in message.tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"모델의 선택    : {tool_name}")  # <- process vs search_memos
        print(f"모델이 만든 인수 : {arguments}")
        result = await mcp_client.call_tool(tool_name, arguments)
        print(f"도구 실행 결과  : {result.data}")
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": str(result.data)}
        )

    final_response = llm.chat.completions.create(model=MODEL, messages=messages)
    print(f"최종 답변     : {final_response.choices[0].message.content}")


async def main():
    server_path = Path(__file__).parent / "server.py"
    transport = FastMCPStdioTransport(str(server_path))
    llm = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    async with Client(transport) as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        print("서버에 등록된 도구:", [t.name for t in mcp_tools])
        llm_tools = to_llm_tools(mcp_tools)
        print("\n모델에게 전달되는 도구 명세:")
        print(json.dumps(llm_tools, ensure_ascii=False, indent=2))

        for user_request in USER_REQUESTS:
            await process_request(llm, mcp_client, llm_tools, user_request)


asyncio.run(main())
