# FastMCP 실습 (섹션 2) - 비동기 외부 API 연동 + 견고한 예외 대응

## 실습 목표

메모 본문을 외부 번역 API로 영어 번역해 첨부하는 도구를 만듭니다.
외부 API는 느리거나 실패할 수 있으므로, **비동기 호출**로 이벤트 루프를 막지 않고,
**타임아웃·재시도·폴백**으로 번역이 실패해도 메모 저장이라는 본질은 지킵니다.
진행 상황과 로그는 FastMCP의 `Context(ctx)`로 클라이언트(AI 호스트)에 전달합니다.

> 이 실습은 커리큘럼의 M8(비동기 외부 API 연동)과 M12(견고한 예외 대응)를 하나로 통합한 것입니다.

---

## 먼저 볼 것: 참고 예시 (완성 코드)

`server.py` 상단의 `cat_fact`(고양이 상식) 도구는 **완성된 참고 예시**입니다.
번역과 도메인만 다를 뿐, 아래 과제와 구현 구조가 똑같습니다 — `httpx.AsyncClient`로 비동기 GET,
`raise_for_status` 후 재시도·지수 백오프·폴백, `ctx.report_progress`/`ctx.info`로 진행 보고.
`fetch_cat_fact`는 `translate_to_en`에, `cat_fact`는 `create_memo`에 대응합니다.
`uv run python client.py`를 실행하면 예시 호출 결과(`[예시] cat_fact ...`)가 먼저 출력됩니다.

---

## 과제: TODO 3곳 채우기

| 위치 | 과제 | 내용 |
|------|------|------|
| `translate_to_en` try 블록 | **[연동 1] 비동기 호출** | `httpx.AsyncClient`로 번역 API를 `await` GET |
| `translate_to_en` except 블록 | **[연동 2] 견고함** | 실패 로그 → 백오프 후 재시도, 끝내 실패하면 `None`(폴백) |
| `create_memo` 본문 | **[연동 3] 컨텍스트** | `report_progress` / `ctx.info`로 진행 상황 보고 |

---

## 핵심 개념

### 1. 왜 비동기인가 — 외부 I/O 동안 이벤트 루프를 놓아준다

번역 API 응답을 기다리는 동안 동기 호출은 스레드를 통째로 붙잡습니다.
`httpx.AsyncClient` + `await`를 쓰면 대기 시간 동안 서버가 다른 요청을 처리할 수 있습니다.

```python
async with httpx.AsyncClient(timeout=TIMEOUT) as client:
    resp = await client.get(TRANSLATE_URL, params={"q": text, "langpair": "ko|en"})
    resp.raise_for_status()
    return resp.json()["responseData"]["translatedText"]
```

### 2. 견고함 — 타임아웃 · 재시도 · 폴백

| 장치 | 역할 |
|------|------|
| `httpx.Timeout(5.0)` | 응답이 5초를 넘으면 끊어 무한 대기를 막는다 |
| 재시도 + 백오프 | 일시적 실패(네트워크 끊김 등)는 잠시 쉬었다 다시 시도 |
| 폴백(`None` 반환) | 끝내 실패하면 번역을 포기하되, **메모 저장은 유지** |

저장을 번역보다 **먼저** 끝내는 순서가 핵심입니다. 외부 의존성이 없는 작업을 먼저 확정해
두면, 뒤따르는 번역이 실패해도 사용자의 메모는 잃지 않습니다.

### 3. Context(ctx) — 서버의 작업 상황을 클라이언트로

`ctx`는 도구가 클라이언트와 소통하는 통로입니다. 긴 작업의 진행률과 로그를 실시간으로 보냅니다.

- `await ctx.report_progress(progress=2, total=3)` → 진행률 (클라이언트의 `progress_handler`가 수신)
- `await ctx.info("...")` → 로그 (클라이언트의 `log_handler`가 수신)

---

## 실행 방법

```bash
uv run python client.py
```

### 예상 출력 (번역 성공)

```
[예시] cat_fact 호출
  [진행] 1/2
  [로그] 고양이 상식 요청 1/2
  [진행] 2/2
  [로그] 완료
[예시] cat_fact 결과: {'status': 'ok', 'fact': 'Cats sleep 70% of their lives.'}

메모 생성 요청: '회의록'
  [진행] 1/3
  [로그] 메모 저장 시작: 회의록
  [진행] 2/3
  [로그] 번역 시도 1/2
  [진행] 3/3
  [로그] 번역 완료
결과: {'status': 'created', 'title': '회의록', 'translated_en': "At today's meeting, we finalized the schedule for next week's launch."}
```

> 번역 문구는 외부 API 상태에 따라 실행마다 조금씩 달라질 수 있습니다.

### 폴백 관찰 (선택)

`server.py`의 `TRANSLATE_URL`을 일부러 잘못된 주소(예: `http://127.0.0.1:9/nope`)로 바꿔 재실행하면,
재시도가 모두 실패한 뒤 폴백 경로가 동작하는 것을 볼 수 있습니다.

```
  [로그] 번역 시도 1/2
  [로그] 번역 실패(1): ConnectError
  [로그] 번역 시도 2/2
  [로그] 번역 실패(2): ConnectError
  [로그] 번역 폴백: 원문만 저장했습니다.
결과: {'status': 'created', 'title': '...', 'translated_en': None, 'note': '번역 서비스를 ...'}
```

번역은 실패했지만 메모는 저장되고, 모델이 상황을 이해할 수 있는 `note`가 함께 반환됩니다.

---

## 학습 포인트 요약

1. 외부 API는 `httpx.AsyncClient` + `await`로 비동기 호출해 대기 동안 이벤트 루프를 막지 않는다.
2. 타임아웃·재시도·폴백으로, 외부 의존성이 실패해도 도구의 핵심 기능(저장)은 보장한다.
3. 외부 의존성이 없는 작업을 먼저 확정하면, 뒤 작업이 실패해도 데이터를 잃지 않는다.
4. `ctx.report_progress`/`ctx.info`로 긴 작업의 진행률과 로그를 클라이언트에 실시간 전달한다.
