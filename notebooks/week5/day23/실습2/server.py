"""실습 1에서 만든 MCP 서버 (완성 제공)

실습 1의 greet 서버에 도구 1개(get_current_time)를 추가한 버전입니다.
도구가 여러 개여야 모델이 '고르는' 모습을 관찰할 수 있습니다.

FastMCP는 함수 정의에서 도구 명세를 자동 생성합니다.
  타입 힌트 -> inputSchema / docstring -> description
모델은 함수 본문을 보지 못하므로, 이 명세는 사람이 아니라 AI가 읽는 문서입니다.
"""

from datetime import datetime

from fastmcp import FastMCP

mcp = FastMCP("Hello MCP")

@mcp.tool
def greet(name: str) -> str:
    """이름을 받아 인사말을 반환합니다."""
    return f"Hello, {name}!"

@mcp.tool
def get_current_time() -> str:
    """현재 날짜와 시간을 반환합니다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    mcp.run()
