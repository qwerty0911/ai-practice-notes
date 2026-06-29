import asyncio
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import FastMCPStdioTransport

async def main():
    # 현재 파일 기준으로 같은 폴더의 server.py 찾기
    server_path = Path(__file__).parent / "server.py"

    # FastMCPStdioTransport를 사용해 server.py 경로로 트랜스포트를 설정하세요.
    transport = FastMCPStdioTransport(str(server_path))

    # TODO: Client(transport)를 async with 문으로 열어 클라이언트를 생성하세요.
    async with Client(transport) as client:
        # TODO: 서버에 등록된 도구 목록을 조회하고 각 도구의 이름을 출력하세요.
        tools = await client.list_tools()
        print("등록된 도구 : ",[t.name for t in tools])

        # TODO: "greet" 도구를 name="Elice" 인수로 호출하세요.
        result = await client.call_tool(
            "greet", {"name" : "Elice"}
        )

        # TODO: 도구가 반환한 실제 값(result.data)을 출력하세요.
        print("result : ", result.data)


asyncio.run(main())
