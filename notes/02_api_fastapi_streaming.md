# OpenAI API, FastAPI, Streaming 정리

## API 기본 호출

OpenAI 호환 API는 클라이언트를 만들고 `chat.completions.create()`를 호출하는 흐름으로 사용했습니다.

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

model_name = os.getenv("MLAPI_MODEL", "openai/gpt-4o-mini")

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "파이썬 데코레이터를 설명해줘."},
    ],
    temperature=0.7,
)
```

주요 파라미터:

- `model`: 사용할 모델 이름
- `messages`: system/user/assistant 대화 목록
- `temperature`: 답변 다양성
- `max_tokens` 또는 `max_completion_tokens`: 출력 길이 제한
- `stream=True`: 토큰 단위 스트리밍

## FastAPI 기본 구조

LLM 호출을 API 서버 뒤에 두면 키 관리, 요청 검증, 공통 로깅, 오류 처리를 서버에서 통제할 수 있습니다.

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    temperature: float = 0.7

class ChatResponse(BaseModel):
    answer: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    answer = call_llm(req.message, temperature=req.temperature)
    return ChatResponse(answer=answer)
```

실습 포인트:

- 요청 모델은 `BaseModel`로 정의
- 필수값, 기본값, 범위 제한은 `Field` 사용
- LLM 호출 함수는 라우터 밖으로 분리
- 인증 오류, rate limit, 서버 오류를 구분해서 처리

## Streaming

스트리밍은 전체 답변이 끝날 때까지 기다리지 않고 chunk를 클라이언트로 흘려보냅니다.

```python
stream = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": message}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="")
```

FastAPI에서는 `StreamingResponse`를 사용합니다.

```python
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def gen():
        stream = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": req.message}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    return StreamingResponse(gen(), media_type="text/plain")
```

## Async Generator

비동기 스트리밍에서는 `async for`로 token stream을 처리합니다.

```python
async def token_stream(text: str, delay: float = 0.2):
    for token in text.split():
        await asyncio.sleep(delay)
        yield token

async def to_upper(stream):
    async for token in stream:
        yield token.upper()
```

## 오류 처리 체크리스트

- API 키 누락: 서버 시작 또는 요청 시 명확한 메시지 반환
- 인증 실패: 401 계열로 변환
- rate limit: 재시도 안내 또는 429 반환
- streaming 중간 실패: 가능한 경우 에러 chunk 반환
- 클라이언트 연결 중단: generator 내부에서 예외 처리
- 사용량 확인: response usage를 별도 필드로 내려주기
