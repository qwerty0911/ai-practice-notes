"""
day22 공통 — RAG Framework 비교용 공유 코퍼스 + MLAPI(OpenAI 호환) 설정.

핵심: day21 의 SAMPLE_DOCS(한국어 10문서)를 재사용해 '같은 코퍼스·같은 질의'로
LlamaIndex / Haystack / DSPy 를 비교한다(6교시 compare_frameworks).

- LLM   : 아래 MLAPI_BASE_URL, MLAPI_API_KEY 문자열을 직접 입력. 각 프레임워크가 base_url/key 로 연결.
- 임베딩: 로컬 HuggingFace multilingual-e5-small (Day21과 동일, 한국어 양호).
"""
import importlib.util
from pathlib import Path

# ── MLAPI (OpenAI 호환 게이트웨이) — 프레임워크별로 이 값들을 주입 ──
MLAPI_BASE_URL = ""
MLAPI_API_KEY  = ""
MLAPI_MODEL    = "openai/gpt-5.4"
EMB_MODEL      = "intfloat/multilingual-e5-small"


# ── 공유 코퍼스 ──
SAMPLE_DOCS = [
    {"id": "doc-rag", "topic": "RAG", "text":
        "RAG(검색 증강 생성, Retrieval-Augmented Generation)는 LLM이 답을 생성하기 전에 "
        "외부 지식 저장소에서 관련 문서를 검색해 프롬프트에 넣어주는 기법이다. 모델의 지식 단절과 "
        "환각 문제를 완화하고, 사내 문서 같은 비공개 지식을 답변 근거로 활용할 수 있게 한다."},
    {"id": "doc-finetune", "topic": "파인튜닝", "text":
        "파인튜닝은 사전학습된 모델의 가중치를 도메인 데이터로 추가 학습시키는 방법이다. 말투·형식·"
        "특정 작업 성능을 끌어올리는 데 강하지만, 최신 사실을 주입하는 데는 부적합하다. 사실 지식이 "
        "자주 바뀌면 RAG가, 행동·스타일을 고정하려면 파인튜닝이 유리하다."},
    {"id": "doc-embedding", "topic": "임베딩", "text":
        "임베딩은 텍스트를 의미가 보존된 고정 길이 벡터로 변환한 것이다. 비슷한 의미의 문장은 벡터 "
        "공간에서 가깝게 위치한다. 임베딩 모델의 언어·도메인 적합성은 검색 품질을 좌우하며, 한국어 "
        "문서에는 다국어 또는 한국어 특화 임베딩 모델을 써야 검색 정확도가 올라간다."},
    {"id": "doc-vectordb", "topic": "벡터DB", "text":
        "벡터 데이터베이스는 임베딩 벡터를 저장하고 질의 벡터와 가장 가까운 벡터를 빠르게 찾아준다. "
        "Chroma는 로컬·경량으로 학습에 적합하고, FAISS는 대규모 인메모리 검색에, pgvector는 PostgreSQL "
        "에 벡터 검색을 더한다. 유사도 척도로는 코사인 유사도가 흔히 쓰인다."},
    {"id": "doc-chunking", "topic": "청킹", "text":
        "청킹은 긴 문서를 검색 단위인 청크로 나누는 과정이다. 청크가 너무 크면 한 청크에 여러 주제가 "
        "섞여 검색 정밀도가 떨어지고, 너무 작으면 문맥이 끊긴다. 보통 수백 토큰 크기에 약간의 overlap을 "
        "두며, 문장·문단 경계를 존중하는 분할이 임의 절단보다 낫다."},
    {"id": "doc-llm", "topic": "LLM", "text":
        "대규모 언어 모델(LLM)은 방대한 텍스트로 사전학습된 트랜스포머 기반 모델로, 다음 토큰을 예측하며 "
        "문장을 생성한다. temperature 같은 디코딩 옵션으로 응답의 창의성과 일관성을 조절한다. 모델은 "
        "학습 시점 이후 지식을 모르며, 모르는 것도 그럴듯하게 지어내는 환각 경향이 있다."},
    {"id": "doc-transformer", "topic": "트랜스포머", "text":
        "트랜스포머는 셀프 어텐션으로 시퀀스 내 토큰 간 관계를 병렬로 학습하는 신경망 구조다. RNN과 달리 "
        "장거리 의존성을 잘 포착하고 병렬화가 쉬워 대규모 학습에 적합하다. 오늘날 대부분의 LLM과 임베딩 "
        "모델이 트랜스포머 인코더/디코더를 기반으로 한다."},
    {"id": "doc-prompt", "topic": "프롬프트", "text":
        "프롬프트 엔지니어링은 모델에게 작업을 지시하는 입력을 설계하는 기술이다. 역할 부여, 예시 제공"
        "(few-shot), 단계적 사고 유도 같은 기법으로 응답 품질을 높인다. RAG에서는 검색된 문맥을 프롬프트에 "
        "넣고 '문맥에 근거해서만 답하라'고 지시하는 것이 환각을 줄이는 핵심이다."},
    {"id": "doc-agent", "topic": "에이전트", "text":
        "AI 에이전트는 LLM에 도구 사용과 판단 루프를 결합해 스스로 다음 행동을 결정하는 시스템이다. "
        "검색·계산·API 호출 같은 도구를 호출하고 결과를 관찰해 목표를 달성한다. RAG와 결합하면 '언제 "
        "검색할지'를 에이전트가 판단하는 구조로 확장된다."},
    {"id": "doc-eval", "topic": "평가", "text":
        "RAG 시스템 평가는 검색 품질(관련 문서를 찾았는가)과 생성 품질(문맥에 충실하고 정확한가)을 함께 "
        "본다. 검색은 recall·precision 으로, 생성은 충실성(faithfulness)·정답성으로 측정한다. 비결정적 "
        "출력 특성상 단일 정답 비교보다 시나리오·루브릭 기반 평가가 적합하다."},
]

EVAL_QUESTION = "RAG와 파인튜닝의 차이는?"     # 6교시 비교 기준 질의
EVAL_QUESTIONS = [
    "RAG와 파인튜닝의 차이는?",
    "벡터 데이터베이스에는 어떤 종류가 있나?",
    "환각을 줄이려면 프롬프트를 어떻게 써야 하나?",
]


def have_mlapi() -> bool:
    return bool(MLAPI_BASE_URL and MLAPI_API_KEY)


def banner(title: str):
    print("=" * 66)
    print(f"📌 {title}")
    print("=" * 66)
