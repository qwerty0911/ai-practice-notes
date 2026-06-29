import asyncio
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport

# [비교 관찰용 - 개발자 직접 호출 방식]
# 어떤 도구를 어떤 인수로 호출할지 개발자가 코드에 미리 정해 둡니다.
# 실행 결과를 host.py(AI 자율 선택 방식)와 비교해 보세요.

async def main():
    # 현재 파일 기준으로 같은 폴더의 server.py 찾기
    server_path = Path(__file__).parent / "server.py"
    transport = FastMCPStdioTransport(str(server_path))

    async with Client(transport) as client:
        tools = await client.list_tools()
        print("등록된 도구:", [t.name for t in tools])

        # 개발자가 도구 이름과 인수를 코드에 직접 지정해서 호출
        result = await client.call_tool("greet", {"name": "Elice"})
        print("greet 결과:", result.data)

        result = await client.call_tool("get_current_time", {})
        print("get_current_time 결과:", result.data)

asyncio.run(main())
