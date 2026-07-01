"""실습 - 견고한 예외 대응: 런타임 예외를 AI 피드백으로 (템플릿)

도구가 '실행되는 동안' 터지는 예외(없는 키, 잘못된 값 등)를 try/except로 잡아,
두 갈래로 분리해 내보냅니다.

  - 서버 로그(상세)  : log.info/exception 으로 내부에 상세히 기록 (개발자·운영용)
  - 모델 메시지(정제) : raw 예외/스택을 노출하지 말고, '무엇이·왜·어떻게'를 담은
                        ToolError로 변환 (AI가 읽고 스스로 고쳐 재시도하게)

핵심: 같은 실패라도 '서버가 보는 것'과 'AI에게 주는 것'은 달라야 한다.
  - P5(Pydantic)는 함수 '실행 전' 스키마 검증이고, 여기서는 '실행 중' 예외 처리다.

과제: 아래 update_memo 를 견고하게 고치세요. (borrow_book 참고 예시를 보되, 그대로 복사하지 말 것)
"""

import logging
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# 서버 로그는 stderr로(클라이언트가 받는 stdout과 분리). 데모에서 눈에 띄게 라벨을 붙인다.
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[서버로그] %(levelname)s %(message)s")
log = logging.getLogger("memo")

mcp = FastMCP("Memo Server")

_MEMOS: dict[str, str] = {"회의록": "RAG 파이프라인 리뷰."}
_BOOKS: dict[str, bool] = {"클린코드": False, "리팩터링": True}  # 제목 -> 대출중 여부


@mcp.tool
def list_memos() -> list[str]:
    """저장된 메모 제목 목록."""
    return list(_MEMOS.keys())


@mcp.tool
def list_books() -> dict:
    """도서 목록과 대출 상태."""
    return dict(_BOOKS)


# ── 참고 예시 (완성본) ──────────────────────────────────────────────
# 메모와 도메인만 다른 '도서 대출'입니다. 실행 중 예외를 try/except로 잡아
# 서버 로그(상세)와 모델 메시지(정제 ToolError)로 분리하는 패턴을 그대로 보여 줍니다.
@mcp.tool
def borrow_book(title: str) -> dict:
    """도서를 대출합니다. (참고 예시)"""
    try:
        borrowed = _BOOKS[title]          # 없는 제목이면 여기서 KeyError (실행 중 예외)
        if borrowed:
            raise ValueError("이미 대출 중")  # 도메인 규칙 위반
        _BOOKS[title] = True
        return {"status": "borrowed", "title": title}
    except KeyError:
        log.info("borrow_book: 없는 제목 요청 title=%r", title)            # 서버 로그(상세)
        raise ToolError(f"'{title}' 도서가 없습니다. list_books로 제목을 확인한 뒤 다시 시도하세요.")
    except ValueError:
        log.info("borrow_book: 중복 대출 시도 title=%r", title)
        raise ToolError(f"'{title}'는 이미 대출 중입니다. 반납 후 다시 시도하세요.")
    except Exception:
        # 예상 못 한 예외: 스택 전체는 서버 로그에만, 모델에는 일반화된 메시지만
        log.exception("borrow_book: 예기치 못한 실패 title=%r", title)
        raise ToolError("대출 처리 중 문제가 발생했습니다. 잠시 후 다시 시도하세요.")


# ── 과제: update_memo 를 견고하게 ────────────────────────────────────
@mcp.tool
def update_memo(title: str, new_content: str) -> dict:
    """기존 메모의 내용을 수정합니다. (없는 제목 수정은 실패해야 한다)"""
    # TODO: 실행 중 발생하는 예외를 try/except로 잡아 견고하게 만드세요. (borrow_book 패턴 참고, 복사 금지)
    #   - 없는 제목을 수정하려 하면 실패해야 한다 → 먼저 _MEMOS[title]로 조회해 KeyError가 나게 하고 잡으세요.
    #   - 빈 내용(new_content.strip()이 빈 값)도 거부하세요.
    #   - 서버 로그에는 상세히(log.info / log.exception), 모델에게는 raw 예외·스택 대신
    #     '무엇이·왜·어떻게'를 담은 정제된 ToolError로 변환하세요.
    #_MEMOS[title] = new_content   # 임시(잘못됨): 지금은 없는 제목도 새로 만들고, 빈 내용도 통과한다
    
    try:
        _MEMOS[title]  # 먼저 조회해서 없는 제목이면 KeyError 발생
        if not new_content.strip():
            raise ValueError("내용이 비어 있습니다. 실제 내용을 입력하세요.")  # 도메인 규칙 위반
        _MEMOS[title] = new_content
        return {"status": "updated", "title": title}
    except KeyError:
        log.info("update_memo : 없는 제목 요청 title=%r", title)            # 서버 로그(상세)
        raise ToolError(f"'{title}' 메모가 없습니다. list_memos로 제목을 확인한 뒤 다시 시도하세요.")
    except ValueError:
        log.info("update_memo : 빈 내용 시도 title=%r", title)
        raise ToolError(f"'{title}'의 내용이 비어 있습니다. 실제 내용을 입력하세요.")
    except Exception:
        # 예상 못 한 예외: 스택 전체는 서버 로그에만, 모델에는 일반화된 메시지만
        log.exception("update_memo : 예기치 못한 실패 title=%r", title)
        raise ToolError("메모 수정 처리 중 문제가 발생했습니다. 잠시 후 다시 시도하세요.")



if __name__ == "__main__":
    mcp.run()
