"""AI 호스트 - 실습 1에서 만든 MCP 서버를 실제 LLM(GPT-5.1)에 연동합니다.

호스트가 자연어 요청 하나를 처리하는 흐름은 6단계입니다.

  1 사용자 요청    : 자연어 요청을 받는다
  2 기능 선택      : Host가 모델에게 도구 목록을 보여주고, 모델이 tool을 선택한다
  3 tool 호출     : 모델의 선택을 받아 호스트가 서버에 실행을 위임한다 (tools/call)
  4 결과 반환      : 서버가 구조화된 실행 결과를 돌려준다
  5 컨텍스트 반영   : 실행 결과를 대화 컨텍스트에 반영한다
  6 최종 응답      : 모델이 결과를 바탕으로 최종 답변을 만든다

여러분의 과제는 이 흐름에서 서버·모델을 잇는 연동 지점 3곳을 완성하는 것입니다.
  [연동 1] 동적 발견      - 서버의 도구 목록을 런타임에 조회 (tools/list)
  [연동 2] 기능 선택 위임  - 발견한 도구 명세를 모델에게 전달
  [연동 3] tool 호출      - 모델이 선택한 도구를 호스트가 실행 (tools/call)
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport
from openai import OpenAI

# .env 파일에서 환경변수(API 키, 엔드포인트)를 로드 - 비밀 값은 코드 밖으로
load_dotenv()

MODEL = "openai/gpt-5.4"

# 모델에게 보낼 자연어 요청 목록
# 어떤 요청이 어떤 도구로 이어지는지 관찰해 보세요.
# (세 번째는 도구 두 개가 필요한 요청, 마지막은 도구가 필요 없는 요청)
# 연동을 완성한 뒤, 자유롭게 요청을 추가하며 모델의 선택이 어떻게 달라지는지 실험해 보세요.
USER_REQUESTS = [
    "엘리스(Elice)에게 인사해 줘.",
    "지금 몇 시야?",
    "엘리스(Elice)에게 인사하고, 지금 몇 시인지도 알려줘.",
    "MCP는 무엇의 약자야?",
]


def to_llm_tools(mcp_tools):
    """MCP 도구 명세를 LLM이 이해하는 형식으로 변환합니다. (완성 제공)

    FastMCP가 자동 생성한 도구 명세가 그대로 모델에게 전달됩니다.
      함수 이름  -> name / docstring -> description / 타입 힌트 -> inputSchema
    모델이 도구에 대해 아는 것은 이 세 가지뿐입니다. 함수 본문은 보지 못합니다.
    """
    # MCP가 처음부터 모델이 소비할 수 있는 표준 형식으로 도구를 명세하기 때문에
    # 변환은 필드를 그대로 옮겨 담는 수준입니다.
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
    """자연어 요청 하나를 6단계 흐름으로 처리하며 모델의 도구 선택을 관찰합니다."""
    print(f"\n{'=' * 60}")
    print(f"사용자 요청    : {user_request}")

    # [1단계 사용자 요청] 대화 컨텍스트 구성
    messages = [
        {
            "role": "system",
            "content": "당신은 MCP 도구를 활용해 사용자를 돕는 AI 비서입니다. "
            "도구로 처리할 수 있는 요청은 직접 답하지 말고 반드시 제공된 도구를 사용하세요.",
        },
        {"role": "user", "content": user_request},
    ]

    # [2단계 기능 선택] 모델 호출 - 도구를 쓸지, 쓴다면 무엇을 쓸지 모델이 판단
    response = llm.chat.completions.create(
        model=MODEL,
        messages=messages,
        # TODO [연동 2 · 기능 선택 위임]: 모델이 서버의 도구를 볼 수 있도록
        #     tools 매개변수로 도구 명세(llm_tools)를 전달하세요.
        #     이 줄이 없으면 모델은 도구의 존재 자체를 모릅니다.
        #     먼저 채우지 않은 채 실행해 보고, 채운 뒤와 결과를 비교해 보세요.
        tools = llm_tools,
    )
    message = response.choices[0].message

    # 모델이 도구를 선택하지 않았다면 답변을 그대로 출력하고 종료
    # (도구를 쓸지 말지도 모델의 판단이라는 점을 관찰하세요)
    if not message.tool_calls:
        print("모델의 선택    : (도구 사용 안 함)")
        print(f"최종 답변     : {message.content}")
        return

    # 모델의 도구 호출 요청(assistant 메시지)을 대화 컨텍스트에 추가
    messages.append(message.model_dump(exclude_none=True))

    for tool_call in message.tool_calls:
        # 모델이 고른 도구 이름과, 모델이 자연어에서 추출해 만든 인수(JSON 문자열)
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"모델의 선택    : {tool_name}")
        print(f"모델이 만든 인수 : {arguments}")

        # [3-4단계 tool 호출과 결과 반환]
        # TODO [연동 3 · tool 호출]: 모델이 고른 도구(tool_name)를 모델이 만든
        #     인수(arguments)로 실행해 반환값을 result에 담으세요.
        #     실습 1에서는 ("greet", {"name": "Elice"})처럼 직접 적었지만,
        #     이제 그 자리에 모델의 선택이 들어갑니다.
        #     실행의 주체는 모델이 아니라 호스트 - 실행 직전에 검토하거나 거부할 수
        #     있으므로, 이 지점이 호스트가 책임지는 신뢰 경계가 됩니다.
        result = await mcp_client.call_tool(tool_name,arguments)

        print(f"도구 실행 결과  : {result.data}")

        # [5단계 컨텍스트 반영] 실행 결과를 대화 컨텍스트에 추가
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result.data),
            }
        )

    # [6단계 최종 응답] 모델이 도구 실행 결과를 바탕으로 최종 답변 생성
    final_response = llm.chat.completions.create(model=MODEL, messages=messages)
    print(f"최종 답변     : {final_response.choices[0].message.content}")


async def main():
    # stdio 트랜스포트 - server.py를 자식 프로세스로 실행해 통신 (실습 1과 동일)
    server_path = Path(__file__).parent / "server.py"
    transport = FastMCPStdioTransport(str(server_path))

    # Host의 LLM 구동 - 외부 모델(GPT-5.1)을 OpenAI 호환 API로 빌려와 사용
    llm = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    async with Client(transport) as mcp_client:
        # TODO [연동 1 · 동적 발견]: 서버에 등록된 도구 목록을 조회해 mcp_tools에 담으세요.
        #     도구 목록은 하드코딩이 아니라 연결 시 런타임에 발견됩니다.
        #     (실습 1에서 배운 메서드를 그대로 사용합니다)
        mcp_tools = await mcp_client.list_tools()

        print("서버에 등록된 도구:", [t.name for t in mcp_tools])

        # 발견한 도구 명세를 모델에게 전달할 형식으로 변환
        llm_tools = to_llm_tools(mcp_tools)

        # 모델에게 전달되는 명세 - 모델이 도구에 대해 아는 전부입니다
        # server.py의 docstring과 타입 힌트가 각각 어디에 들어갔는지 찾아보세요
        print("\n모델에게 전달되는 도구 명세:")
        print(json.dumps(llm_tools, ensure_ascii=False, indent=2))

        for user_request in USER_REQUESTS:
            await process_request(llm, mcp_client, llm_tools, user_request)


asyncio.run(main())
