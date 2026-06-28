# Advanced RAG Search 정리

Week 5 Day 21은 RAG 시스템에서 검색 품질을 높이는 방법을 단계적으로 비교한 실습입니다. 단순 벡터 검색에서 끝내지 않고, 청킹 전략, 임베딩 모델, 하이브리드 검색, 쿼리 변환, 리랭킹을 조합해 end-to-end RAG 파이프라인으로 확장했습니다.

## 1. 청킹 전략

RAG에서 검색 단위는 chunk입니다. 같은 문서라도 `chunk_size`와 `chunk_overlap`에 따라 검색 결과가 달라집니다.

- 작은 chunk: 세밀하게 검색되지만 문맥이 끊길 수 있음
- 큰 chunk: 문맥은 풍부하지만 여러 주제가 섞여 검색 정밀도가 떨어질 수 있음
- overlap: chunk 경계에서 잘리는 문맥을 보완

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
)
chunks = splitter.split_documents(docs)
```

핵심은 정답 chunk 크기를 고정값으로 외우는 것이 아니라, 데이터와 질문 유형에 맞춰 실험으로 정하는 것입니다.

## 2. 검색 품질 진단

검색이 틀릴 때는 답변만 보지 않고, 먼저 어떤 문서가 몇 점으로 검색됐는지 확인해야 합니다.

확인할 항목:

- `top_k`를 바꿨을 때 관련 문서가 포함되는지
- top-1 점수가 충분히 높은지
- 한국어 문서에 맞는 임베딩 모델을 사용했는지
- 무관한 chunk가 context에 섞여 토큰 비용과 답변 품질을 떨어뜨리지 않는지

한국어 검색에서는 영어 위주 임베딩보다 다국어 또는 한국어 특화 임베딩이 유리합니다.

```python
EMB_KO = "intfloat/multilingual-e5-small"
EMB_EN = "sentence-transformers/all-MiniLM-L6-v2"
```

## 3. Hybrid Search

BM25와 벡터 검색은 강점이 다릅니다.

- BM25: 정확한 키워드, 고유명사, 약어에 강함
- 벡터 검색: 표현이 달라도 의미가 비슷한 문서를 찾는 데 강함

하이브리드 검색은 두 검색 결과를 함께 사용해 한쪽이 놓친 문서를 다른 쪽이 보완하도록 만듭니다. 실습에서는 Reciprocal Rank Fusion(RRF)로 순위 기반 결합을 구현했습니다.

```python
def rrf_fuse(result_lists, k=60, top_n=5):
    scores, docmap = {}, {}
    for docs in result_lists:
        for rank, doc in enumerate(docs):
            key = doc.page_content
            docmap[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [docmap[key] for key, _ in ranked[:top_n]]
```

## 4. Query Transformation

사용자 질문이 짧거나 모호하면 문서와 어휘가 달라 검색 누락이 생깁니다. 이를 보완하기 위해 질문 자체를 검색 친화적으로 바꿉니다.

대표 기법:

- Multi-Query: LLM으로 질문을 여러 표현으로 확장한 뒤 각각 검색
- HyDE: 질문에 대한 가상 답변을 만들고, 그 답변 문장으로 검색

```python
variants = multi_query(llm, question, n=3)
hyde_query = hyde(llm, question)
```

Multi-Query는 recall을 넓히는 데 좋고, HyDE는 질문과 문서 사이의 어휘 격차를 줄이는 데 도움이 됩니다. 대신 둘 다 LLM 호출 비용이 생기므로 검색 실패가 잦은 구간에 선택적으로 적용하는 것이 좋습니다.

## 5. Reranking

1차 검색기는 빠르게 후보를 넓게 가져오지만, 최종 순위가 항상 정확하지는 않습니다. Reranking은 1차 후보를 Cross-Encoder로 다시 점수화해 Top-K 품질을 높이는 2단계 검색 방식입니다.

흐름:

1. Bi-Encoder 기반 벡터 검색으로 후보를 넓게 회수
2. Cross-Encoder가 `(query, document)` 쌍을 함께 보고 관련성 점수 계산
3. 점수순으로 재정렬한 상위 문서만 LLM context로 전달

한국어 문서에는 다국어 리랭커를 선택하는 것이 중요합니다.

```python
reranked_docs = rerank(
    query,
    candidate_docs,
    top_n=3,
    model="BAAI/bge-reranker-v2-m3",
)
```

## 6. Modular RAG Pipeline

마지막 실습에서는 개별 기법을 하나의 파이프라인으로 조립했습니다.

```text
Question
-> Multi-Query
-> Hybrid Search(BM25 + Vector + RRF)
-> Cross-Encoder Rerank
-> Generate
```

이 구조의 핵심은 recall과 precision을 나누어 개선하는 것입니다.

- Multi-Query와 Hybrid Search: 관련 후보를 최대한 놓치지 않게 회수
- Reranking: 회수된 후보 중 질문에 가장 맞는 문서만 정밀 선택
- Generate: 선택된 context에 근거해 답변 생성

## 체크리스트

- 청킹 크기와 overlap을 데이터 기준으로 실험했는가?
- 검색 결과의 점수와 순위를 직접 확인했는가?
- 한국어 문서에 적합한 임베딩 모델을 사용했는가?
- BM25와 벡터 검색의 약점을 하이브리드 검색으로 보완했는가?
- 짧거나 모호한 질문에 Query Transformation을 적용할 수 있는가?
- 최종 context에 들어갈 문서를 Reranking으로 정밀하게 줄였는가?

