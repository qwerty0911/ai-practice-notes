"""개발자 직접 호출 클라이언트 - 진행 보고/로그/번역 결과를 관찰합니다. (정답)

서버가 ctx.report_progress로 보내는 진행률과 ctx.info로 보내는 로그를
핸들러로 받아 출력하고, 번역이 첨부된 최종 결과를 확인합니다.

마지막에 '구현 점검' 요약을 출력합니다. 진행률 보고 수신 건수(연동3)는 외부 번역
API 상태와 무관하므로, template(미구현)과 answer(정답)를 항상 결정적으로 구분합니다.
"""

import asyncio
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport


async def on_log(params):
    """서버의 ctx.info 로그를 받아 출력합니다."""
    print(f"  [로그] {params.data['msg']}")


def make_progress_handler(counter: dict):
    """진행률을 출력하면서 수신 건수를 counter['n']에 누적하는 핸들러를 만듭니다."""

    async def on_progress(progress: float, total: float | None, message: str | None):
        counter["n"] += 1
        print(f"  [진행] {progress:.0f}/{total:.0f}")

    return on_progress


async def main():
    transport = FastMCPStdioTransport(str(Path(__file__).parent / "server.py"))
    async with Client(transport, log_handler=on_log) as client:
        # 참고 예시 tool을 먼저 호출해 비동기+진행보고+폴백 패턴을 확인합니다 (완성 제공).
        print("[예시] cat_fact 호출")
        ex_prog = {"n": 0}
        example = await client.call_tool(
            "cat_fact", {}, progress_handler=make_progress_handler(ex_prog)
        )
        print("[예시] cat_fact 결과:", example.data)

        print("\n메모 생성 요청: '회의록'")
        prog = {"n": 0}
        result = await client.call_tool(
            "create_memo",
            {"title": "회의록", "content": "오늘 회의에서 다음 주 출시 일정을 확정했습니다."},
            progress_handler=make_progress_handler(prog),
        )
        print("결과:", result.data)

        # ── 구현 점검: template(미완성)과 answer(정답)를 결정적으로 구분 ──
        translated = result.data.get("translated_en")
        print("\n── 구현 점검 (연동 1·2·3) ──")
        print(f"  [연동3] 진행률 보고 수신: {prog['n']}건   (정답=3, 미구현=0)")
        print(f"  [연동1·2] 번역 결과: {translated if translated else '폴백(None)'}")
        if prog["n"] == 3 and translated:
            print("  => 구현 완료: 연동 1·2·3 모두 동작")
        elif prog["n"] == 3 and not translated:
            print("  => 연동3 동작. 번역은 폴백(외부 API 실패 또는 연동1·2 미구현) "
                  "- 위 로그의 '번역 완료/폴백'으로 확인")
        else:
            print("  => 미완성: 진행률 0건이면 연동3 미구현, 번역 폴백이면 연동1·2 미구현 "
                  "- server.py의 TODO를 채우세요")
        print("  (진행률 보고 건수는 외부 API 상태와 무관하므로 template/answer 구분 기준입니다)")


asyncio.run(main())
