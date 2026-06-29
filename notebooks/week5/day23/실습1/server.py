from fastmcp import FastMCP

# TODO: FastMCP 인스턴스를 생성하고 서버 이름을 "Hello MCP"로 지정하세요.
mcp = FastMCP("Hello MCP")

# TODO: @mcp.tool 데코레이터를 추가하여 아래 함수를 MCP 도구로 등록하세요.
@mcp.tool
def greet(name: str) -> str:         # 타입 힌트 -> 입력 스키마
    '''인사합니다'''
    # TODO: f-string을 사용해 "Hello, {name}!" 형태의 인사말을 반환하세요.
    return f"Hello, {name}!!!"

if __name__ == "__main__":
    # TODO: stdio 방식으로 서버를 실행하세요.
    mcp.run()
