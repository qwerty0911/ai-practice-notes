"""실습 - 도구 명세에 따른 AI 선택 변화 관찰 (템플릿)

같은 일을 하는 도구 두 개를, 이름과 설명(description)만 다르게 등록합니다.
모델은 함수 본문을 보지 못하고 명세(이름·description·입력 스키마)만 보고 고르므로,
명세의 구체성이 선택을 가릅니다.

두 도구는 내부적으로 완전히 같은 _search()를 호출합니다. 동작은 같고 명세만 다릅니다.

과제: 두 도구의 docstring(=모델이 읽는 description)을 서로 다르게 작성하세요.
  [명세 A] process      - 일부러 '모호하게' (예: "데이터를 처리합니다.")
  [명세 B] search_memos - '구체적으로' (무엇을 어떻게 찾는지 명시)
그리고 host.py를 실행해, 같은 요청에 모델이 어느 도구를 고르는지 비교하세요.
"""

from fastmcp import FastMCP

mcp = FastMCP("Memo Search Server")

# 검색 대상이 되는 샘플 메모 (제목 -> 내용)
_MEMOS = {
    "회의록 2026-06-13": "RAG 파이프라인 리뷰. 다음 주 출시 일정 확정.",
    "장보기": "우유, 달걀, 커피 원두",
    "독서 메모": "Designing Data-Intensive Applications 3장 정리",
}


def _search(keyword: str) -> list[str]:
    """제목이나 내용에 keyword가 포함된 메모의 제목 목록을 돌려줍니다. (두 도구가 공유)"""
    return [title for title, content in _MEMOS.items()
            if keyword in title or keyword in content]


@mcp.tool
def process(query: str) -> list[str]:
    # TODO [명세 A]: 일부러 '모호한' 한 줄 docstring을 작성하세요.
    #     모델이 이 도구가 '메모 검색'에 쓰인다는 것을 추론하기 어렵게.
    return _search(query)


@mcp.tool
def search_memos(keyword: str) -> list[str]:
    # TODO [명세 B]: '구체적인' docstring을 작성하세요.
    #     무엇을(메모) 어떻게(키워드 포함) 찾는지 명시하고, 짧은 예시를 덧붙이세요.
    return _search(keyword)


if __name__ == "__main__":
    mcp.run()
