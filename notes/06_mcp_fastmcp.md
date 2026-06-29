# MCP와 FastMCP 정리

Week 5 Day 23은 FastMCP로 MCP 서버를 만들고, 직접 호출 방식과 LLM Host 연동 방식을 비교한 실습입니다. 핵심은 도구를 제공하는 서버, 도구를 호출하는 클라이언트, 자연어 요청을 보고 도구를 선택하는 AI Host의 역할을 분리해서 이해하는 것입니다.

## 1. MCP란?

MCP(Model Context Protocol)는 AI 모델과 외부 기능 제공자 사이의 표준 통신 규약입니다.

- MCP Server: 모델이 사용할 수 있는 도구를 제공
- MCP Client/Host: 서버에 연결해 도구 목록을 조회하고 도구를 호출
- Tool: 서버에 등록된 실행 가능한 함수
- Tool schema: 도구 이름, 설명, 입력 파라미터 구조

모델은 함수 본문을 직접 보는 것이 아니라, 도구의 이름, docstring, 타입 힌트에서 만들어진 명세를 보고 어떤 도구를 쓸지 판단합니다.

## 2. FastMCP 서버

FastMCP에서는 일반 파이썬 함수에 `@mcp.tool`을 붙이면 MCP 도구로 등록됩니다.

```python
from fastmcp import FastMCP

mcp = FastMCP("Hello MCP")

@mcp.tool
def greet(name: str) -> str:
    """이름을 받아 인사말을 반환합니다."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

중요한 점:

- `FastMCP("Hello MCP")`: 서버 인스턴스 생성
- `@mcp.tool`: 함수를 MCP 도구로 등록
- 타입 힌트: 입력 JSON schema로 변환
- docstring: 모델이 읽는 도구 설명으로 사용
- `mcp.run()`: stdio 방식으로 서버 실행

`mcp.run()`은 `if __name__ == "__main__":` 아래에 두는 것이 안전합니다. 클라이언트가 서버 파일을 import하거나 subprocess로 실행하는 과정에서 이벤트 루프가 중복 실행되는 문제를 피할 수 있습니다.

## 3. FastMCP 클라이언트 직접 호출

실습 1의 클라이언트는 서버를 stdio subprocess로 실행하고, 개발자가 직접 도구 이름과 인수를 지정해 호출합니다.

```python
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport

server_path = Path(__file__).parent / "server.py"
transport = FastMCPStdioTransport(str(server_path))

async with Client(transport) as client:
    tools = await client.list_tools()
    result = await client.call_tool("greet", {"name": "Elice"})
```

흐름:

1. `FastMCPStdioTransport`가 `server.py`를 subprocess로 실행
2. `Client`가 stdio를 통해 서버와 연결
3. `list_tools()`로 등록된 도구 목록 조회
4. `call_tool()`로 도구 이름과 인수를 직접 지정해 실행

이 방식은 단순하고 명확하지만, 어떤 도구를 쓸지 개발자가 코드에 미리 정해야 합니다.

## 4. AI Host 연동

실습 2에서는 MCP 서버를 LLM Host에 연결합니다. 사용자는 자연어로 요청하고, 모델이 도구 명세를 보고 필요한 도구를 선택합니다.

처리 흐름:

1. 사용자 요청을 messages에 담음
2. Host가 MCP 서버에서 도구 목록을 동적으로 조회
3. MCP 도구 명세를 LLM tool 형식으로 변환
4. 모델 호출 시 `tools` 매개변수로 도구 명세 전달
5. 모델이 tool call과 arguments를 생성
6. Host가 `mcp_client.call_tool()`로 실제 도구 실행
7. 실행 결과를 tool 메시지로 대화 컨텍스트에 추가
8. 모델을 다시 호출해 최종 자연어 답변 생성

```python
mcp_tools = await mcp_client.list_tools()
llm_tools = to_llm_tools(mcp_tools)

response = llm.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=llm_tools,
)
```

모델이 도구를 선택하면 Host가 실행합니다.

```python
for tool_call in message.tool_calls:
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    result = await mcp_client.call_tool(tool_name, arguments)
```

## 5. 직접 호출과 AI Host 방식 비교

| 기준 | 직접 호출 Client | AI Host |
| --- | --- | --- |
| 도구 선택 | 개발자가 코드에 지정 | 모델이 자연어 요청을 보고 선택 |
| 인수 생성 | 개발자가 직접 작성 | 모델이 요청에서 추출 |
| 도구 목록 | 개발자가 알고 있어야 함 | 런타임에 동적 발견 |
| 흐름 | 고정된 호출 흐름 | 요청에 따라 달라지는 동적 흐름 |
| 적합한 경우 | 테스트, 단순 자동화 | AI 비서, Agent, 동적 tool use |

## 6. 신뢰 경계

모델은 도구 호출을 "요청"할 뿐, 실제 실행 주체는 Host입니다.

따라서 Host는 다음 지점에서 책임을 져야 합니다.

- 모델이 선택한 도구 이름이 허용된 도구인지 확인
- 모델이 만든 arguments가 안전한지 검증
- 민감한 도구는 사용자 승인 후 실행
- 파일 삭제, 결제, 외부 전송 같은 위험 작업은 별도 권한 정책 적용

이번 실습은 학습 목적상 모델의 선택을 바로 실행하지만, 실제 서비스에서는 allowlist, schema validation, user confirmation 같은 실행 통제가 필요합니다.

## 7. 실습 체크리스트

- `@mcp.tool`로 파이썬 함수를 MCP 도구로 등록할 수 있는가?
- 타입 힌트와 docstring이 도구 명세에 어떻게 반영되는지 설명할 수 있는가?
- `list_tools()`와 `call_tool()`의 역할을 구분할 수 있는가?
- stdio transport가 서버 프로세스를 어떻게 연결하는지 이해했는가?
- LLM이 tool call을 만들고 Host가 실행하는 역할 분리를 설명할 수 있는가?
- 도구 실행 직전이 Host의 신뢰 경계라는 점을 이해했는가?

