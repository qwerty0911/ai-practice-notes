# RAG Framework 비교 정리

Week 5 Day 22는 같은 한국어 코퍼스와 같은 질문을 기준으로 LlamaIndex, Haystack, DSPy의 RAG 구현 방식을 비교한 실습입니다. 핵심은 "어떤 프레임워크가 더 좋다"보다, 각 프레임워크가 RAG의 어느 부분을 잘 추상화하는지 구분하는 것입니다.

## 1. 비교 기준

공통 조건:

- 동일 코퍼스: AI/LLM 도메인 한국어 문서 10개
- 동일 임베딩 모델: `intfloat/multilingual-e5-small`
- 동일 평가 질문: `RAG와 파인튜닝의 차이는?`
- 동일 목적: 검색 결과, 답변, 출처, 실행 흐름 비교

비교 대상:

- LlamaIndex: 데이터 인덱싱과 QueryEngine 중심
- Haystack: 컴포넌트 기반 Pipeline 중심
- DSPy: Signature, Module, Optimizer 중심

## 2. LlamaIndex

LlamaIndex는 문서를 인덱스로 구성하고, QueryEngine을 통해 질의하는 흐름이 중심입니다.

주요 개념:

- `Document`: 원본 문서 단위
- `VectorStoreIndex`: 임베딩 기반 검색형 QA에 적합
- `SummaryIndex`: 전체 문서 요약에 적합
- `TreeIndex`: 계층적 요약/탐색에 적합
- `query_engine`: 인덱스를 질의 가능한 인터페이스로 변환

```python
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()
response = query_engine.query(question)
```

정리:

- 문서 인덱싱, 검색, 요약 흐름을 빠르게 구성하기 좋음
- "데이터를 어떻게 읽고 검색할 것인가"가 중요한 RAG에 잘 맞음
- 작업 목적에 따라 index 종류를 고르는 판단이 중요함

## 3. Haystack

Haystack은 RAG를 컴포넌트 그래프로 조립합니다. 각 단계가 명확한 컴포넌트로 분리되어 있어 운영 파이프라인을 설계하기 좋습니다.

주요 컴포넌트:

- `DocumentStore`: 문서 저장소
- `DocumentEmbedder`: 문서 임베딩 생성
- `TextEmbedder`: 질문 임베딩 생성
- `Retriever`: 관련 문서 검색
- `PromptBuilder`: 검색 문맥을 프롬프트로 구성
- `Generator`: LLM 답변 생성
- `DocumentJoiner`: 여러 검색 결과 결합
- `Ranker`: 후보 문서 재정렬

```python
pipeline = Pipeline()
pipeline.add_component("text_embedder", text_embedder)
pipeline.add_component("retriever", retriever)
pipeline.add_component("prompt_builder", prompt_builder)
pipeline.add_component("generator", generator)
```

정리:

- 각 단계가 독립 컴포넌트라 구조가 명확함
- Hybrid Search, Joiner, Ranker처럼 검색 파이프라인을 확장하기 좋음
- `pipeline.dump()`로 YAML 직렬화가 가능해 운영/재현성 측면에서 유리함

## 4. DSPy

DSPy는 프롬프트를 직접 문자열로 길게 작성하기보다, 입력과 출력의 형태를 Signature로 정의하고 Module로 프로그램처럼 구성합니다.

주요 개념:

- `Signature`: 입력/출력 스펙 정의
- `Module`: RAG 같은 프로그램 단위 정의
- `ChainOfThought`: 추론 과정을 포함한 생성 모듈
- `forward`: 검색과 생성을 연결하는 실행 로직

```python
class GenerateAnswer(dspy.Signature):
    context = dspy.InputField()
    question = dspy.InputField()
    answer = dspy.OutputField()

class RAG(dspy.Module):
    def __init__(self, k=3):
        super().__init__()
        self.k = k
        self.generate = dspy.ChainOfThought(GenerateAnswer)
```

정리:

- RAG를 프롬프트 묶음이 아니라 프로그램 단위로 다루기 좋음
- Signature와 Module로 구조화된 LLM 프로그램을 만들 수 있음
- 검색기는 직접 구현하거나 별도 retriever와 연결할 수 있음

## 5. DSPy Optimizer

DSPy Optimizer는 예시 데이터와 metric을 이용해 프롬프트를 자동으로 개선합니다.

실습 흐름:

1. RAG Module 정의
2. trainset/devset 구성
3. metric 함수로 정답 기준 정의
4. `BootstrapFewShot`으로 compile
5. compile 전후 dev 정확도와 프롬프트 변화 비교

```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(metric=metric)
compiled = optimizer.compile(base_rag, trainset=trainset)
```

정리:

- 프롬프트 개선을 감으로 하지 않고 데이터와 평가 기준으로 수행
- few-shot 예시가 자동으로 프롬프트에 반영됨
- 작은 devset이라도 base와 compiled 결과를 비교하면 개선 방향을 볼 수 있음

## 6. 프레임워크 선택 기준

| 기준 | LlamaIndex | Haystack | DSPy |
| --- | --- | --- | --- |
| 강점 | 인덱싱/검색형 QA | 운영형 파이프라인 | LLM 프로그램 최적화 |
| 중심 추상화 | Index, QueryEngine | Component, Pipeline | Signature, Module |
| 잘 맞는 상황 | 문서 기반 QA를 빠르게 구성 | 검색-생성 단계를 명확히 조립 | 프롬프트/모듈을 데이터로 개선 |
| 확장 포인트 | Index 종류 선택 | Joiner, Ranker, YAML | Optimizer, metric |

## 체크리스트

- 같은 코퍼스와 같은 질문으로 비교했는가?
- 답변뿐 아니라 출처와 지연 시간도 함께 봤는가?
- 검색 중심 문제인지, 운영 파이프라인 문제인지, 프롬프트 최적화 문제인지 구분했는가?
- 프레임워크별 추상화 단위(Index, Pipeline, Module)를 설명할 수 있는가?
- DSPy Optimizer에서 metric과 train/dev 데이터의 역할을 이해했는가?

