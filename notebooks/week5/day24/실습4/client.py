"""개발자 직접 호출 클라이언트 - 실패가 모델에게 어떻게 전달되는지 관찰합니다. (정답)

도구가 실행 중 실패하면, 서버는 상세 로그를 [서버로그]로 stderr에 남기고,
모델(=이 클라이언트)에게는 정제된 ToolError 메시지만 돌려줍니다.
아래 출력의 '모델 수신' 줄이 바로 AI가 읽고 고쳐 재시도할 단서입니다.
"""

import asyncio
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport


def msg(e: Exception) -> str:
    """ToolError 메시지(모델이 받는 정제된 안내)에서 핵심 한 줄만 추립니다."""
    return str(e).splitlines()[0]


async def call(client, tool: str, args: dict, label: str):
    try:
        result = await client.call_tool(tool, args)
        print(f"[{label}] 성공: {result.data}")
    except Exception as e:
        print(f"[{label}] 모델 수신(ToolError): {msg(e)}")


async def main():
    transport = FastMCPStdioTransport(str(Path(__file__).parent / "server.py"))
    async with Client(transport) as client:
        print("== 참고 예시: borrow_book (도서 대출) ==")
        await call(client, "borrow_book", {"title": "클린코드"}, "정상 대출")
        await call(client, "borrow_book", {"title": "없는책"}, "없는 제목")
        await call(client, "borrow_book", {"title": "리팩터링"}, "이미 대출중")

        print("\n== 과제: update_memo (메모 수정) ==")
        await call(client, "update_memo", {"title": "회의록", "new_content": "출시 일정 확정"}, "정상 수정")
        await call(client, "update_memo", {"title": "없는메모", "new_content": "내용"}, "없는 제목")
        await call(client, "update_memo", {"title": "회의록", "new_content": "   "}, "빈 내용")

        print("\n최종 메모:", (await client.call_tool("list_memos", {})).data)


asyncio.run(main())
