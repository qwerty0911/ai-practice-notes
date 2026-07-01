"""실습 - 비동기 외부 API 연동 + 견고한 예외 대응 (정답)

메모를 저장하면서, 본문을 영어로 자동 번역해 첨부하는 도구를 만듭니다.
번역은 외부 API에 의존하므로 느리거나 실패할 수 있습니다. 핵심은 두 가지입니다.

  - 비동기 연동 : httpx.AsyncClient로 외부 API를 await 호출해 이벤트 루프를 막지 않는다
  - 견고함     : 타임아웃·재시도·폴백으로, 번역이 실패해도 '메모 저장'이라는 본질은 지킨다

진행 상황과 로그는 FastMCP의 Context(ctx)로 클라이언트(=AI 호스트)에 전달합니다.
  ctx.report_progress(...) : 진행률 보고 / ctx.info(...) : 클라이언트로 로그 전송
"""

import asyncio

import httpx
from fastmcp import Context, FastMCP

mcp = FastMCP("Memo Server")

# 생성된 메모를 보관하는 임시 저장소 (서버 프로세스 메모리)
_MEMOS: dict[str, dict] = {}

# 외부 번역 API (키 불필요). 한국어 -> 영어.
TRANSLATE_URL = "https://api.mymemory.translated.net/get"
# TRANSLATE_URL = "https://localhost/nope"  # 잘못된 API 로 실행. 폴백 확인용
TIMEOUT = httpx.Timeout(5.0)  # 응답이 5초를 넘으면 끊는다 (무한 대기 방지)
MAX_RETRIES = 2  # 일시적 실패에 대비한 재시도 횟수

# 참고 예시용 외부 API (키 불필요). 고양이 상식 한 줄을 돌려준다.
CAT_FACT_URL = "https://catfact.ninja/fact"


# ── 참고 예시 (완성본) ──────────────────────────────────────────────
# 번역과 도메인만 다른 '고양이 상식' 도구입니다. 구현 구조는 아래 과제와 똑같습니다.
#   httpx 비동기 GET + raise_for_status + 재시도/지수 백오프/폴백 + ctx 진행보고
# fetch_cat_fact는 translate_to_en에, cat_fact는 create_memo에 대응합니다.
async def fetch_cat_fact(ctx: Context) -> str | None:
    """고양이 상식을 가져옵니다. 모든 시도가 실패하면 None을 반환(폴백 신호)합니다."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await ctx.info(f"고양이 상식 요청 {attempt}/{MAX_RETRIES}")
            # async with: 호출이 끝나면 연결을 정리. 타임아웃으로 무한 대기 차단.
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(CAT_FACT_URL)
                resp.raise_for_status()  # 4xx/5xx면 예외 발생
                return resp.json()["fact"]
        except (httpx.HTTPError, KeyError) as e:
            await ctx.info(f"요청 실패({attempt}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                # 지수 백오프(0.5초 → 1초 → 2초 …)로 대기 후 재시도
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
    return None  # 폴백: 기본 메시지로 진행하라는 신호


@mcp.tool
async def cat_fact(ctx: Context) -> dict:
    """고양이 상식 한 줄을 가져옵니다. 실패하면 기본 메시지로 폴백합니다. (참고 예시)"""
    await ctx.report_progress(progress=1, total=2)
    fact = await fetch_cat_fact(ctx)
    await ctx.report_progress(progress=2, total=2)
    if fact is None:
        await ctx.info("폴백: 기본 메시지를 반환합니다.")
        return {"status": "ok", "fact": None,
                "note": "상식 서비스를 일시적으로 사용할 수 없습니다."}
    await ctx.info("완료")
    return {"status": "ok", "fact": fact}


# ── 여기부터 과제: 위 예시를 참고해 translate_to_en / create_memo를 완성하세요 ──
async def translate_to_en(text: str, ctx: Context) -> str | None:
    """본문을 영어로 번역합니다. 모든 시도가 실패하면 None을 반환(폴백 신호)합니다."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await ctx.info(f"번역 시도 {attempt}/{MAX_RETRIES}")
            # async with: 호출이 끝나면 연결을 정리. 타임아웃으로 무한 대기 차단.
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    TRANSLATE_URL, params={"q": text, "langpair": "ko|en"}
                )
                resp.raise_for_status()  # 4xx/5xx면 예외 발생
                return resp.json()["responseData"]["translatedText"]
        except (httpx.HTTPError, KeyError) as e:
            # 네트워크/타임아웃/응답형식 오류를 한데 모아 처리
            await ctx.info(f"번역 실패({attempt}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                # 지수 백오프(0.5초 → 1초 → 2초 …)로 대기 후 재시도
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
    return None  # 폴백: 번역 없이 진행하라는 신호


@mcp.tool
async def create_memo(title: str, content: str, ctx: Context) -> dict:
    """메모를 저장하고, 본문을 영어로 자동 번역해 첨부합니다.

    번역 API가 느리거나 실패해도 메모 저장 자체는 보장합니다(폴백).
    """
    await ctx.report_progress(progress=1, total=3)
    await ctx.info(f"메모 저장 시작: {title}")

    # 1) 저장은 외부 의존성이 없으므로 먼저 보장한다
    record: dict = {"title": title, "content": content, "translated_en": None}
    _MEMOS[title] = record
    await ctx.report_progress(progress=2, total=3)

    # 2) 번역은 외부 API에 의존 -> 실패해도 위에서 저장은 이미 끝났다(폴백)
    translated = await translate_to_en(content, ctx)
    await ctx.report_progress(progress=3, total=3)

    if translated is None:
        await ctx.info("번역 폴백: 원문만 저장했습니다.")
        record["note"] = "번역 서비스를 일시적으로 사용할 수 없어 원문만 저장했습니다."
        return {"status": "created", "title": title, "translated_en": None,
                "note": record["note"]}

    record["translated_en"] = translated
    await ctx.info("번역 완료")
    return {"status": "created", "title": title, "translated_en": translated}


if __name__ == "__main__":
    mcp.run()
