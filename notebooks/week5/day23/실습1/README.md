# FastMCP 실습 1 - 나의 첫 번째 MCP 서버

## 실습 목표

FastMCP 라이브러리를 사용해 가장 간단한 MCP 서버를 만들고, 클라이언트에서 해당 서버에 연결하여 도구를 호출하는 전체 흐름을 익힙니다.

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `server.py` | FastMCP 서버 — `greet` 도구를 등록하고 stdio로 실행 |
| `client.py` | FastMCP 클라이언트 — 서버에 연결하고 `greet` 도구를 호출 |

---

## 핵심 개념

### 1. MCP (Model Context Protocol)

AI 모델(클라이언트)과 외부 기능 제공자(서버) 사이의 표준 통신 규약입니다.  
서버는 **도구(tool)** 를 등록하고, 클라이언트는 해당 도구를 조회·호출합니다.

### 2. FastMCP 서버 구성 요소 (`server.py`)

```python
from fastmcp import FastMCP

mcp = FastMCP("Hello MCP")      # 서버 인스턴스 생성 (서버 이름 지정)

@mcp.tool                        # 함수를 MCP 도구로 등록
def greet(name: str) -> str:    # 타입 힌트 → 입력 스키마 자동 생성
    """이름을 받아 인사말을 반환합니다."""  # docstring → 도구 설명 자동 생성
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()                    # stdio 방식으로 서버 실행
```

> `mcp.run()`은 반드시 `if __name__ == "__main__":` 안에서 호출해야 합니다.
> 클라이언트가 서버를 띄울 때 사용하는 `fastmcp run` 명령은 server.py를 import한 뒤 서버를 실행하는데,
> `mcp.run()`이 모듈 최상위에 있으면 import 시점에 실행되어
> `RuntimeError: Already running asyncio in this thread` 오류로 서버가 종료됩니다.

| 구성 요소 | 설명 |
|-----------|------|
| `FastMCP("이름")` | 서버 인스턴스 생성. 인수는 서버 이름 |
| `@mcp.tool` | 파이썬 함수를 MCP 도구로 등록하는 데코레이터 |
| 타입 힌트 | 도구의 입력 JSON 스키마로 자동 변환됨 |
| docstring | 클라이언트가 도구를 식별할 수 있도록 설명으로 노출됨 |
| `mcp.run()` | stdio를 통해 서버를 실행 (프로세스 간 통신). `if __name__ == "__main__":` 안에서 호출 |

### 3. FastMCP 클라이언트 흐름 (`client.py`)

```python
import asyncio
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport

async def main():
    # 현재 파일 기준으로 같은 폴더의 server.py 찾기
    server_path = Path(__file__).parent / "server.py"
    transport = FastMCPStdioTransport(str(server_path))   # stdio 트랜스포트 설정

    async with Client(transport) as client:               # 서버에 연결
        tools = await client.list_tools()                 # 등록된 도구 목록 조회
        print("등록된 도구:", [t.name for t in tools])

        result = await client.call_tool("greet", {"name": "Elice"})  # 도구 호출
        print("결과:", result.data)                       # 반환값 출력

asyncio.run(main())
```

| 단계 | 설명 |
|------|------|
| `Path(__file__).parent / "server.py"` | 실행 위치와 무관하게 client.py와 같은 폴더의 server.py를 가리킴 |
| `FastMCPStdioTransport` | 서버 스크립트를 subprocess로 실행하여 stdio로 연결 |
| `Client(transport)` | 트랜스포트를 기반으로 MCP 클라이언트 생성 |
| `list_tools()` | 서버에 등록된 도구 목록을 반환 |
| `call_tool(name, args)` | 지정한 도구를 인수와 함께 호출 |
| `result.data` | 도구가 반환한 실제 값 |
| `asyncio.run(main())` | 클라이언트 API는 비동기이므로 async 함수로 작성하고 이벤트 루프에서 실행 |

---

## 실행 방법

```bash
# 클라이언트를 실행하면 서버가 자동으로 subprocess로 실행됩니다
uv run python client.py
```

### 예상 출력

```
등록된 도구: ['greet']
결과: Hello, Elice!
```

---

## 학습 포인트 요약

1. `@mcp.tool` 데코레이터 하나로 일반 파이썬 함수를 MCP 도구로 등록할 수 있다.
2. 타입 힌트와 docstring이 자동으로 MCP 스키마와 설명으로 변환된다.
3. stdio 트랜스포트를 통해 클라이언트가 서버를 subprocess로 실행하고 통신한다.
4. 클라이언트는 `list_tools` → `call_tool` 순서로 도구를 사용한다.
