# FastMCP 실습 (섹션 2) - Pydantic 기반 도구 인자 검증

## 실습 목표

도구의 입력을 신뢰하지 않고 검증하는 두 가지 층을 구현합니다.
타입·길이 같은 **스키마 검증**은 Pydantic 모델 정의만으로 함수 실행 전에 자동 적용하고,
중복 제목처럼 스키마로 표현할 수 없는 **비즈니스 규칙**은 함수 안에서 `ToolError`로 처리합니다.
검증 실패 메시지가 모델(AI)에게 어떻게 전달되는지, 그 메시지를 어떻게 써야 하는지를 관찰합니다.

---

## 먼저 볼 것: 참고 예시 (완성 코드)

`server.py` 상단의 `add_contact`(연락처) 도구는 **완성된 참고 예시**입니다.
메모와 도메인만 다를 뿐, 아래 과제와 구현 구조가 똑같습니다 — `Field` 길이·`description` 제약,
`field_validator`로 공백 차단, 중복 시 `ToolError`. 이 예시를 그대로 따라 메모 도구를 완성하세요.
`uv run python client.py`를 실행하면 예시 호출 결과(`[예시] add_contact: ...`)가 먼저 출력됩니다.

---

## 과제: TODO 3곳 채우기

| 위치 | 과제 | 내용 |
|------|------|------|
| `MemoInput.title` / `content` | **[검증 1] 스키마 제약** | `Field`로 길이 제한과 `description` 부여 |
| `MemoInput.title_not_blank` | **[검증 2] 비즈니스 규칙** | 공백만으로 된 제목을 `field_validator`로 차단 |
| `create_memo` 본문 | **[검증 3] 명확한 에러** | 중복 제목일 때 모델이 고칠 수 있는 `ToolError` 메시지 작성 |

---

## 핵심 개념

### 1. 스키마 검증 — 모델 정의가 곧 입력 게이트

`MemoInput`을 도구의 인자로 선언하면, FastMCP가 모델에서 `inputSchema`를 자동 생성합니다.
`Field(min_length=..., max_length=...)`로 단 제약은 JSON 스키마의 `minLength`/`maxLength`가 되어
**함수가 실행되기 전에** 검증되고, 위반 시 함수 본문은 아예 실행되지 않습니다.

```python
class MemoInput(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=50, description="메모 제목 (1~50자)")]
    content: Annotated[str, Field(min_length=1, max_length=2000, description="메모 본문 (1~2000자)")]
```

### 2. field_validator — 타입으로 표현할 수 없는 규칙

`min_length=1`은 `"   "`(공백 3칸)을 통과시킵니다. "의미 있는 제목"이라는 규칙은 타입이 아니라
`@field_validator`로 표현합니다. 여기서 던진 `ValueError`의 메시지가 그대로 클라이언트에 전달됩니다.

### 3. ToolError — AI에게 전달할 명확한 에러

스키마 검증 에러는 Pydantic이 만든 다소 장황한 메시지지만, 비즈니스 규칙 위반은
`ToolError("...")`로 **한 줄짜리 명확한 메시지**를 직접 만들 수 있습니다.
모델이 다음 행동(다른 제목 사용/기존 메모 수정)을 고를 수 있도록 "무엇을 어떻게 고칠지"를 담습니다.

> 모델은 함수 본문을 보지 못합니다. 필드 `description`과 에러 메시지가 곧 AI가 읽는 명세입니다.

---

## 실행 방법

```bash
uv run python client.py
```

### 예상 출력

```
[예시] add_contact: {'status': 'created', 'name': '홍길동'}

[정상] title='회의록 2026-06-13'
  성공 : {'status': 'created', 'title': '회의록 2026-06-13', 'content_length': 33}

[field_validator 위반 (공백 제목)] title='   '
  검증 실패 : 1 validation error for call[create_memo] / memo.title / Value error, 제목은 공백만으로 채울 수 없습니다. 내용을 요약한 제목을 지정하세요. ...

[max_length 위반 (제목 길이 초과)] title='xxxxxxxx...'
  검증 실패 : 1 validation error for call[create_memo] / memo.title / String should have at most 50 characters ...

[비즈니스 규칙 위반 (중복 제목)] title='회의록 2026-06-13'
  검증 실패 : '회의록 2026-06-13' 제목의 메모가 이미 있습니다. 다른 제목을 쓰거나 기존 메모를 수정하세요.

저장된 메모 제목: ['회의록 2026-06-13']
```

> 스키마 검증 실패(앞 두 건)는 Pydantic이 만든 장황한 메시지, 비즈니스 규칙 실패(마지막)는
> `ToolError`로 직접 쓴 한 줄 메시지입니다. 두 메시지의 결을 비교해 보세요.

---

## 학습 포인트 요약

1. Pydantic 모델을 도구 인자로 쓰면 타입·길이 제약이 자동으로 `inputSchema`가 되고 함수 실행 전에 검증된다.
2. 타입으로 표현할 수 없는 규칙은 `@field_validator`로, 그 `ValueError` 메시지가 그대로 클라이언트에 전달된다.
3. 비즈니스 규칙 위반은 `ToolError`로 한 줄짜리 명확한 메시지를 만들어 모델의 재시도를 유도한다.
4. 모델이 보는 것은 명세(필드 description·에러 메시지)뿐이므로, 검증 메시지는 곧 AI 인터페이스다.
