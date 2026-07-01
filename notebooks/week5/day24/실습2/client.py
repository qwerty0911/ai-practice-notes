"""개발자 직접 호출 클라이언트 - 검증 동작을 정상/실패 케이스로 관찰합니다. (정답)

정상 입력 1건과 검증 실패 3건을 차례로 호출해, 서버가 돌려주는 에러 메시지를 확인합니다.
이 메시지는 AI 호스트 환경에서 모델에게 그대로 전달되어, 모델이 인수를 고쳐 재시도하는 단서가 됩니다.
"""

import asyncio
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport

# (제목, 내용, 설명) - 정상 1건 + 검증 실패 3건
CASES = [
    ("회의록 2026-06-13", "RAG 파이프라인 리뷰. 다음 주 액션 아이템 세 건 정리.", "정상"),
    ("   ", "제목이 공백만으로 채워진 경우", "field_validator 위반 (공백 제목)"),
    ("x" * 60, "제목이 50자를 넘는 경우", "max_length 위반 (제목 길이 초과)"),
    ("회의록 2026-06-13", "같은 제목으로 다시 생성", "비즈니스 규칙 위반 (중복 제목)"),
]


def first_line(text: str) -> str:
    """여러 줄 에러 메시지에서 핵심이 담긴 부분만 추려 출력합니다."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " / ".join(lines[:3])


async def main():
    transport = FastMCPStdioTransport(str(Path(__file__).parent / "server.py"))
    async with Client(transport) as client:
        # 참고 예시 tool을 먼저 호출해 정상 동작을 확인합니다 (완성 제공).
        example = await client.call_tool(
            "add_contact", {"contact": {"name": "홍길동", "phone": "010-1234-5678"}}
        )
        print("[예시] add_contact:", example.data)

        for title, content, desc in CASES:
            print(f"\n[{desc}] title={title!r}")
            try:
                result = await client.call_tool(
                    "create_memo", {"memo": {"title": title, "content": content}}
                )
                print("  성공 :", result.data)
            except Exception as e:
                # 검증 실패 시 서버가 돌려준 에러 메시지 (모델이 인수를 고치는 단서)
                print("  검증 실패 :", first_line(str(e)))

        titles = await client.call_tool("list_memos", {})
        print("\n저장된 메모 제목:", titles.data)


asyncio.run(main())
