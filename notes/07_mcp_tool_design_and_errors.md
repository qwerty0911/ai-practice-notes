# MCP 도구 설계와 견고한 실행 정리

Week 5 Day 24는 FastMCP 기반 도구를 더 안전하고 AI 친화적으로 설계하는 실습입니다. Day 23에서 MCP 서버, 클라이언트, AI Host의 기본 연결을 다뤘다면, Day 24는 도구 명세, 입력 검증, 외부 API 연동, 예외 처리처럼 실제 기능 구현에서 중요한 부분을 다룹니다.

## 1. 도구 명세가 AI 선택을 좌우한다

모델은 MCP 도구의 함수 본문을 보지 못합니다. 모델이 보는 것은 도구 이름, docstring에서 생성된 description, 타입 힌트에서 생성된 input schema입니다.

실습 1에서는 내부적으로 같은 `_search()` 함수를 호출하는 도구 두 개를 만들고, 이름과 설명만 다르게 둡니다.

```python
@mcp.tool
def process(query: str) -> list[str]:
    return _search(query)

@mcp.tool
def search_memos(keyword: str) -> list[str]:
    return _search(keyword)
```

두 도구의 동작은 같지만, `process`처럼 모호한 이름과 설명보다 `search_memos`처럼 목적이 드러나는 이름과 구체적인 docstring이 모델의 선택을 더 안정적으로 만듭니다.

핵심:

- docstring은 단순 주석이 아니라 AI가 읽는 API 문서
- 도구 이름은 짧지만 강한 선택 단서
- description은 언제, 무엇을, 어떤 인자로 처리하는지 알려야 함
- 같은 기능이라도 명세가 모호하면 모델이 도구를 잘못 고르거나 아예 쓰지 않을 수 있음

좋은 명세는 이렇게 씁니다.

```python
@mcp.tool
def search_memos(keyword: str) -> list[str]:
    """키워드가 제목이나 본문에 포함된 메모를 검색하고, 일치하는 메모 제목 목록을 반환합니다."""
    return _search(keyword)
```

## 2. Pydantic으로 도구 인자 검증하기

실습 2는 메모 생성 도구의 입력을 두 층으로 검증합니다.

- 스키마 검증: 타입, 길이, 필수 여부처럼 구조적으로 표현 가능한 제약
- 비즈니스 검증: 공백 제목, 중복 제목처럼 도메인 규칙에 가까운 제약

Pydantic 모델을 도구 인자로 사용하면 FastMCP가 input schema를 자동 생성하고, 함수 실행 전에 검증합니다.

```python
from typing import Annotated
from pydantic import BaseModel, Field, field_validator

class MemoInput(BaseModel):
    title: Annotated[
        str,
        Field(min_length=1, max_length=50, description="메모 제목 (1~50자)")
    ]
    content: Annotated[
        str,
        Field(min_length=1, max_length=2000, description="메모 본문 (1~2000자)")
    ]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("제목은 공백만으로 채울 수 없습니다. 내용을 요약한 제목을 지정하세요.")
        return stripped
```

중복 제목처럼 저장소 상태를 봐야 하는 규칙은 함수 내부에서 `ToolError`로 처리합니다.

```python
from fastmcp.exceptions import ToolError

@mcp.tool
def create_memo(memo: MemoInput) -> dict:
    """제목과 내용을 받아 메모를 저장하고, 저장 결과를 반환합니다."""
    if memo.title in _MEMOS:
        raise ToolError(
            f"'{memo.title}' 제목의 메모가 이미 있습니다. 다른 제목을 쓰거나 기존 메모를 수정하세요."
        )
    _MEMOS[memo.title] = memo.content
    return {"status": "created", "title": memo.title}
```

핵심:

- `Field` 제약은 함수 실행 전에 막는 입력 게이트
- `field_validator`는 타입만으로 표현하기 어려운 규칙을 검증
- `ToolError`는 모델이 읽고 다음 행동을 정할 수 있는 명확한 에러 메시지
- 필드 description과 에러 메시지도 AI 인터페이스의 일부

## 3. 비동기 외부 API 연동과 폴백

실습 3은 메모를 저장하면서 외부 번역 API를 호출해 영어 번역을 첨부합니다.

외부 API는 느리거나 실패할 수 있으므로 다음 전략을 사용합니다.

- `httpx.AsyncClient`와 `await`로 비동기 호출
- `httpx.Timeout`으로 무한 대기 방지
- 재시도와 지수 백오프로 일시적 실패 대응
- 끝내 실패하면 `None`을 반환해 폴백
- 메모 저장은 외부 API보다 먼저 완료해서 핵심 기능 보장

```python
async def translate_to_en(text: str, ctx: Context) -> str | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await ctx.info(f"번역 시도 {attempt}/{MAX_RETRIES}")
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    TRANSLATE_URL,
                    params={"q": text, "langpair": "ko|en"},
                )
                resp.raise_for_status()
                return resp.json()["responseData"]["translatedText"]
        except (httpx.HTTPError, KeyError) as e:
            await ctx.info(f"번역 실패({attempt}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
    return None
```

긴 작업의 진행 상황은 FastMCP `Context`로 클라이언트에 전달합니다.

```python
@mcp.tool
async def create_memo(title: str, content: str, ctx: Context) -> dict:
    await ctx.report_progress(progress=1, total=3)
    await ctx.info(f"메모 저장 시작: {title}")

    record = {"title": title, "content": content, "translated_en": None}
    _MEMOS[title] = record
    await ctx.report_progress(progress=2, total=3)

    translated = await translate_to_en(content, ctx)
    await ctx.report_progress(progress=3, total=3)
```

핵심:

- 외부 I/O는 비동기로 처리해 이벤트 루프를 막지 않음
- 실패 가능한 외부 의존성보다 핵심 저장 작업을 먼저 확정
- 재시도 후에도 실패하면 기능 전체를 실패시키지 않고 폴백
- `ctx.report_progress`와 `ctx.info`는 AI Host가 사용자에게 진행 상황을 설명할 수 있는 단서

## 4. 런타임 예외를 AI 피드백으로 바꾸기

실습 4는 함수 실행 중에 발생하는 예외를 잡아 서버 로그와 모델 메시지로 분리합니다.

Pydantic 검증은 함수 실행 전의 입력 게이트입니다. 하지만 없는 메모 수정, 이미 대출 중인 도서 처리, 외부 상태 충돌처럼 실행 중에야 알 수 있는 실패는 `try/except`로 처리해야 합니다.

```python
@mcp.tool
def update_memo(title: str, new_content: str) -> dict:
    """기존 메모의 내용을 수정합니다."""
    try:
        _MEMOS[title]
        if not new_content.strip():
            raise ValueError("내용이 비어 있습니다.")
        _MEMOS[title] = new_content
        return {"status": "updated", "title": title}
    except KeyError:
        log.info("update_memo: 없는 제목 요청 title=%r", title)
        raise ToolError(f"'{title}' 메모가 없습니다. list_memos로 제목을 확인한 뒤 다시 시도하세요.")
    except ValueError:
        log.info("update_memo: 빈 내용 시도 title=%r", title)
        raise ToolError("새 내용이 비어 있습니다. 수정할 내용을 입력하세요.")
    except Exception:
        log.exception("update_memo: 예기치 못한 실패 title=%r", title)
        raise ToolError("메모 수정 처리 중 문제가 발생했습니다. 잠시 후 다시 시도하세요.")
```

핵심:

- 서버 로그에는 개발자/운영자가 볼 상세 정보를 남김
- 모델에게는 raw exception이나 stack trace를 노출하지 않음
- `ToolError`에는 무엇이 문제인지, 다음에 무엇을 해야 하는지 포함
- 좋은 에러 메시지는 모델의 자기 교정을 돕는 피드백

## 5. 실무 체크리스트

- 도구 이름만 보고도 용도를 짐작할 수 있는가?
- docstring에 언제 이 도구를 써야 하는지 분명히 적었는가?
- 입력 필드 description이 모델이 인자를 만들기에 충분한가?
- 타입/길이/필수 여부는 Pydantic schema로 검증했는가?
- 도메인 규칙 위반은 `ToolError`로 명확하게 설명했는가?
- 외부 API 호출에는 timeout, retry, fallback이 있는가?
- 장시간 작업은 `Context`로 진행률과 로그를 보고하는가?
- 서버 로그와 모델에게 전달되는 메시지를 분리했는가?
- 에러 메시지에 모델이 다음에 취할 행동을 담았는가?

