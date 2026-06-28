"""
day21 공통 모듈 — MLAPI(LLM) · HuggingFace 임베딩 · 한국어 샘플 문서.

- LLM: .env 또는 환경변수의 MLAPI_BASE_URL, MLAPI_API_KEY, MLAPI_MODEL 값으로 연결.
- 임베딩: 로컬 HuggingFace(무료). 기본은 다국어 e5, 교시6 에서 영어 위주 모델과 비교.
- 데이터: 인터넷 의존 없는 결정론적 한국어 문서 10개(AI/LLM 도메인).
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings


# ── LLM (MLAPI) ───────────────────────────────────────────────
load_dotenv()

MLAPI_BASE_URL = os.getenv("MLAPI_BASE_URL", "https://mlapi.run/v1")
MLAPI_API_KEY = os.getenv("MLAPI_API_KEY")
MLAPI_MODEL = os.getenv("MLAPI_MODEL", "openai/gpt-5.4")


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    """환경변수에 설정된 MLAPI 정보로 ChatOpenAI 생성."""
    if not MLAPI_API_KEY:
        raise ValueError("MLAPI_API_KEY 환경변수 또는 .env 값을 설정하세요.")
    return ChatOpenAI(
        model=MLAPI_MODEL,
        base_url=MLAPI_BASE_URL,
        api_key=MLAPI_API_KEY,
        temperature=temperature,
    )


# ── 임베딩 (로컬 HuggingFace) ─────────────────────────────────
# 첫 실행 시 자동 다운로드(HF 캐시). 한 번 받으면 캐시 재사용.
EMB_KO = "intfloat/multilingual-e5-small"            # ~470MB, 다국어(한국어 양호) — 기본
EMB_EN = "sentence-transformers/all-MiniLM-L6-v2"    # ~90MB,  영어 위주(한국어 약함) — 교시6 비교용

_emb_cache: dict = {}


def get_embeddings(model_name: str = EMB_KO) -> HuggingFaceEmbeddings:
    """임베딩 모델 로드(프로세스 내 캐시). model_name 으로 교체해 검색 품질 비교."""
    if model_name not in _emb_cache:
        _emb_cache[model_name] = HuggingFaceEmbeddings(model_name=model_name)
    return _emb_cache[model_name]


# ── 한국어 샘플 문서 (AI/LLM 도메인 10개) ─────────────────────
# RAG 데모가 의미 있도록 서로 구분되는 주제로 구성. metadata 로 출처 추적.
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


def sample_documents():
    """SAMPLE_DOCS 를 LangChain Document 리스트로 변환."""
    from langchain_core.documents import Document
    return [Document(page_content=d["text"], metadata={"id": d["id"], "topic": d["topic"]})
            for d in SAMPLE_DOCS]


# ── RAG 기법 비교용 코퍼스 (검색 비교 실습 3~6교시) ─────────────────────────
# BDAI rag01~rag07 실습의 코퍼스를 재사용. 각 문서가 "하나의 RAG 기법"을 설명해
# topic·id 가 곧 정답(target)이 되도록 설계 → BM25 vs Vector blind spot 을
# '정답 문서의 순위(rank)'로 또렷이 비교할 수 있다(rag02 방식).
# SAMPLE_DOCS(일반 AI 주제)와 분리해 두어 01·02교시·day22 코퍼스에 영향 없음.
RAG_TECH_DOCS = [
    {"id": "doc01", "topic": "벡터검색", "text":
        "벡터 검색은 텍스트를 고차원 임베딩 벡터로 변환한 뒤 코사인 유사도 같은 지표로 가까운 문서를 "
        "찾는 검색 방식이다. 의미가 유사하면 단어가 달라도 검색되지만, 정확한 키워드 일치는 약하다."},
    {"id": "doc02", "topic": "BM25", "text":
        "BM25 는 단어 빈도와 문서 길이를 고려해 점수를 매기는 전통적인 키워드 검색 알고리즘이다. "
        "정확한 단어 일치에 강하고 인덱싱이 빠르지만, 동의어나 의미 유사성은 잡지 못한다."},
    {"id": "doc03", "topic": "하이브리드", "text":
        "하이브리드 검색은 BM25 같은 sparse 검색과 임베딩 기반 dense 검색을 결합해 각자의 약점을 "
        "보완한다. 두 결과의 점수를 가중 합산하거나 reciprocal rank fusion(RRF) 같은 방법으로 통합한다."},
    {"id": "doc04", "topic": "리랭킹", "text":
        "Cross-Encoder 리랭커는 질의와 문서를 함께 입력 받아 관련성 점수를 직접 계산하는 모델이다. "
        "1차 검색이 추려준 후보 20~100개를 정밀하게 재정렬해 Top-K 품질을 크게 끌어올린다. "
        "비용이 비싸 1차 검색에는 쓰지 않는다."},
    {"id": "doc05", "topic": "Cohere리랭크", "text":
        "Cohere Rerank API 는 다국어를 지원하는 상용 리랭커 서비스다. rerank-multilingual-v3.0 모델은 "
        "한국어를 포함한 100개 이상 언어를 처리한다. API 호출 비용이 발생하므로 후보 수와 호출 빈도를 관리해야 한다."},
    {"id": "doc06", "topic": "쿼리변환", "text":
        "MultiQueryRetriever 는 LLM 으로 원본 질의를 여러 표현으로 다시 작성한 뒤, 각각의 변형 질의로 "
        "검색을 수행하고 결과를 합집합으로 결합한다. 사용자의 짧은 질의를 다양한 각도로 풀어내어 검색 누락을 줄인다."},
    {"id": "doc07", "topic": "컨텍스트압축", "text":
        "컨텍스트 압축은 검색된 문서 전문을 그대로 LLM 에 넣지 않고, 질의와 관련된 문장만 추출해 토큰 "
        "비용을 절약하는 기법이다. LLMChainExtractor 는 LLM 자체에게 관련 부분 추출을 맡기는 방식이다."},
    {"id": "doc08", "topic": "청킹", "text":
        "RAG 의 청크 분할 전략은 검색 품질에 큰 영향을 준다. 너무 잘게 자르면 맥락이 끊기고, 너무 크게 "
        "잡으면 검색 정확도가 떨어진다. 일반적으로 500~1500 토큰 범위에서 의미 단위로 자르고, 200 정도의 오버랩을 둔다."},
    {"id": "doc09", "topic": "보안", "text":
        "프롬프트 인젝션은 사용자 입력에 포함된 악의적 지시문이 시스템 프롬프트나 검색된 문서에 섞여 "
        "들어가 LLM 의 행동을 조작하는 보안 위협이다. RAG 시스템은 외부 문서를 컨텍스트로 주입하므로 특히 주의가 필요하다."},
    {"id": "doc10", "topic": "LangChain마이그레이션", "text":
        "LangChain 1.x 부터 일부 retriever 가 langchain.retrievers 에서 langchain_classic.retrievers 로 "
        "이동했다. 0.x 에서 작성된 코드는 import 경로를 수정해야 동작한다. EnsembleRetriever, "
        "MultiQueryRetriever, ContextualCompressionRetriever 가 대표적이다."},
]


def rag_tech_documents():
    """RAG_TECH_DOCS 를 LangChain Document 리스트로 변환(검색 비교 실습용).
    문서가 짧아 1청크=1문서이므로 별도 청킹 없이 검색기에 바로 넣는다."""
    from langchain_core.documents import Document
    return [Document(page_content=d["text"], metadata={"id": d["id"], "topic": d["topic"]})
            for d in RAG_TECH_DOCS]


def rank_of(target_id: str, docs):
    """검색 결과에서 특정 문서 id 의 순위(1-based). 결과에 없으면 None.
    정답 문서가 '몇 위로 잡혔는가'로 검색기를 비교한다(낮을수록 좋음)."""
    for i, d in enumerate(docs, 1):
        if d.metadata.get("id") == target_id:
            return i
    return None


# ===========================================================================
# 고급 검색 헬퍼 (4~6교시: 하이브리드 · 쿼리변환 · 리랭킹 · 모듈러 파이프라인)
# ---------------------------------------------------------------------------
# langchain.retrievers 의 EnsembleRetriever/MultiQueryRetriever 는 현재 yeardream의
# langchain 0.3.30 ↔ langchain-core 0.3.86 버전 스큐로 import 가 깨진다.
# 그래서 RRF 융합·멀티쿼리를 직접 구현한다(더 교육적이고 버전 의존도 낮음).
# ===========================================================================
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


# ── 인덱싱 ────────────────────────────────────────────────
def build_chunks(chunk_size: int = 300, overlap: int = 50):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap).split_documents(sample_documents())


def build_vector_retriever(chunks, k: int = 5, model: str = EMB_KO, name: str = "day21_adv"):
    vs = Chroma.from_documents(chunks, get_embeddings(model), collection_name=name)
    return vs.as_retriever(search_kwargs={"k": k})


def build_bm25(chunks, k: int = 5):
    from langchain_community.retrievers import BM25Retriever
    r = BM25Retriever.from_documents(chunks)   # 공백 토큰화(한국어는 형태소 분석 권장)
    r.k = k
    return r


# ── 융합(RRF) ─────────────────────────────────────────────
def rrf_fuse(result_lists, k: int = 60, top_n: int = 5):
    """여러 검색 결과(문서 리스트)를 Reciprocal Rank Fusion 으로 융합.
    점수 체계가 다른(BM25 점수 vs 코사인) 결과를 '순위' 기반으로 안전하게 합친다."""
    scores, docmap = {}, {}
    for docs in result_lists:
        for rank, d in enumerate(docs):
            key = d.page_content
            docmap[key] = d
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [docmap[key] for key, _ in ranked[:top_n]]


# ── 쿼리 변환 ─────────────────────────────────────────────
def multi_query(llm, q: str, n: int = 3):
    """LLM 으로 질문을 서로 다른 표현의 검색 질의 n개로 늘린다(원 질문 포함)."""
    text = llm.invoke(
        f"다음 질문을 검색이 잘 되도록 서로 다른 표현의 검색 질의 {n}개로 바꿔줘. "
        f"각 줄에 하나씩, 번호·기호 없이.\n질문: {q}"
    ).content
    qs = [ln.strip("-•* \t") for ln in text.splitlines() if ln.strip()]
    return [q] + qs[:n]


def hyde(llm, q: str):
    """HyDE — 질문에 대한 '가상의 답변'을 만들어 그걸로 검색(문서와 어휘가 비슷해 적중↑)."""
    return llm.invoke(
        f"다음 질문에 대한 가상의 짧은 답변을 1~2문장으로 써줘(사실 여부 무관, 검색용).\n질문: {q}"
    ).content


# ── 재순위화(Cross-Encoder) ───────────────────────────────
# 모델별로 캐시(여러 리랭커를 한 노트북에서 비교할 수 있게).
# 기본 ms-marco 는 영어 위주(데모용). 한국어는 다국어 BAAI/bge-reranker-v2-m3 가 정석.
_ce_cache: dict = {}
def get_cross_encoder(model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    if model not in _ce_cache:
        from sentence_transformers import CrossEncoder
        _ce_cache[model] = CrossEncoder(model, max_length=512)
    return _ce_cache[model]


def rerank(query: str, docs, top_n: int = 3,
           model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """1차 후보를 Cross-Encoder 로 (질문,문서) 쌍 점수화해 재정렬.
    ms-marco 는 영어 위주(데모). 한국어 품질은 BAAI/bge-reranker-v2-m3(다국어) 권장 — model 인자로 교체."""
    ce = get_cross_encoder(model)
    scores = ce.predict([(query, d.page_content) for d in docs])
    return [d for _, d in sorted(zip(scores, docs), key=lambda x: -float(x[0]))][:top_n]
