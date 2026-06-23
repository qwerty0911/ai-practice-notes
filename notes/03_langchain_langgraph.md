# LangChain과 LangGraph 정리

## LangChain 기본 구성 요소

### Prompt

프롬프트는 모델에게 줄 입력 템플릿입니다.

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}"),
])
```

### LLM

실습에서는 OpenAI 호환 API와 Ollama 로컬 모델을 모두 사용했습니다.

```python
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

llm = ChatOpenAI(model_name="openai/gpt-4o-mini", temperature=0)
local_llm = ChatOllama(model="llama3.1")
route_llm = ChatOllama(model="llama3.2:3B", format="json", temperature=0)
```

### OutputParser

모델 출력을 원하는 형태로 변환합니다.

```python
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

text_parser = StrOutputParser()
json_parser = JsonOutputParser()
```

### Chain

LangChain Expression Language(LCEL)에서는 `|`로 컴포넌트를 연결합니다.

```python
chain = prompt | llm | StrOutputParser()
answer = chain.invoke({"question": "RAG가 뭐야?"})
```

`RunnablePassthrough()`는 입력을 그대로 다음 단계에 넘길 때 씁니다.

```python
from langchain_core.runnables import RunnablePassthrough

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

## RAG 구성 요소

### DocumentLoader

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader(doc_path)
docs = loader.load()
```

### TextSplitter

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
split_docs = text_splitter.split_documents(docs)
```

주요 파라미터:

- `chunk_size`: 한 chunk의 최대 길이
- `chunk_overlap`: chunk 사이에 겹쳐둘 길이

### Embedding과 Vector DB

```python
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings,
)

retriever = vectorstore.as_retriever()
```

Vector DB 선택:

- `Chroma`: 로컬 저장과 persist directory 구성에 편함
- `FAISS`: 빠른 유사도 검색과 `save_local/load_local` 캐싱에 편함

## LangGraph 기본 구조

LangGraph는 LLM 앱을 상태 기반 그래프로 구성합니다.

```python
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph

class State(TypedDict):
    question: str
    generation: str
    documents: list

workflow = StateGraph(State)
```

## Node 함수 단위

노드는 `State`를 입력받고, 업데이트할 값을 dict로 반환하는 함수로 작성합니다.

```python
def init_answer(state: State) -> State:
    question = state["question"]
    route = route_chain.invoke({"question": question})
    return {"generation": route}

def retrieval(state: State) -> State:
    docs = retriever.invoke(state["question"])
    return {"documents": docs}

def answer_with_retrieved_data(state: State) -> State:
    answer = rag_chain.invoke({
        "question": state["question"],
        "context": state["documents"],
    })
    return {"generation": answer}

def answer(state: State) -> State:
    answer = plain_chain.invoke({"question": state["question"]})
    return {"generation": answer}
```

노드 설계 기준:

- 하나의 노드는 하나의 책임만 갖기
- LLM 라우팅, 검색, 답변 생성, 검증을 함수로 분리
- 상태 key 이름을 일관되게 유지
- 출력은 다음 노드가 사용할 최소 필드만 반환

## Edge와 Conditional Edge

기본 edge는 고정된 다음 노드로 이동합니다.

```python
workflow.add_node("init_answer", init_answer)
workflow.add_node("rag", retrieval)
workflow.add_node("plain_answer", answer)
workflow.add_node("answer_with_retrieval", answer_with_retrieved_data)

workflow.set_entry_point("init_answer")
workflow.add_edge("plain_answer", END)
workflow.add_edge("rag", "answer_with_retrieval")
workflow.add_edge("answer_with_retrieval", END)
```

조건부 edge는 상태나 평가 함수 결과에 따라 다음 노드를 고릅니다.

```python
workflow.add_conditional_edges(
    "init_answer",
    route_question,
    {
        "rag": "rag",
        "plain_answer": "plain_answer",
    },
)

graph = workflow.compile()
response = graph.invoke({"question": "질문"})
```

## 실습별 그래프 패턴

### 엑셀 + PDF 챗봇

노드:

- `init_answer`: 질문 라우팅
- `excel_data`: 엑셀 데이터 질의용 Python 코드 생성/실행
- `rag`: PDF 검색
- `excel_plot`: 그래프 생성
- `answer_with_data`: 엑셀 분석 결과 기반 답변
- `answer_with_retrieval`: RAG 문서 기반 답변
- `plain_answer`: 일반 답변

분기:

- 엑셀 질문이면 `excel_data`
- PDF 문서 질문이면 `rag`
- 그래프 요청이면 `excel_plot`
- 일반 질문이면 `plain_answer`

### Self-RAG

노드:

- `rag`: 문서 검색
- `answer_with_retrieval`: 검색 문서 기반 답변 생성
- `plain_answer`: 검색 없이 답변

검증 함수:

- `is_data_relevant`: 검색 문서가 질문과 관련 있는지 평가
- `is_answer_supportive`: 답변이 검색 문서에 의해 지지되는지 평가
- `is_answer_useful`: 답변이 질문에 충분히 유용한지 평가
- `is_hallucinated`: 답변의 할루시네이션 여부 평가

조건부 흐름:

```python
workflow.add_conditional_edges(
    "rag",
    lambda state: is_data_relevant(state)["relevant"],
    {
        "yes": "answer_with_retrieval",
        "no": "plain_answer",
    },
)

workflow.add_conditional_edges(
    "answer_with_retrieval",
    judge_answer,
    {
        "yes": END,
        "no": "plain_answer",
        "hallucinated": "answer_with_retrieval",
    },
)
```

### Adaptive RAG

Adaptive RAG는 내부 문서 검색과 웹 검색을 함께 라우팅합니다.

노드:

- `init_answer`: 질문을 `excel_data`, `rag`, `web_search`, `plain_answer` 중 하나로 라우팅
- `web_search`: Tavily 등 웹 검색
- `rag`: 내부 Vector DB 검색
- `answer_with_web_retrieval`: 웹 검색 결과 기반 답변
- `answer_with_retrieval`: 내부 문서 기반 답변

핵심 조건부 edge:

```python
workflow.add_conditional_edges(
    "init_answer",
    lambda state: state["generation"].lower().strip(),
    {
        "excel_data": "excel_data",
        "rag": "rag",
        "plain_answer": "plain_answer",
        "web_search": "web_search",
    },
)

workflow.add_conditional_edges(
    "web_search",
    lambda state: is_data_relevant(state)["relevant"],
    {
        "yes": "answer_with_web_retrieval",
        "no": "plain_answer",
    },
)

workflow.add_conditional_edges(
    "answer_with_web_retrieval",
    judge_answer,
    {
        "yes": END,
        "no": "plain_answer",
        "hallucinated": "web_search",
    },
)
```

## LangGraph 체크리스트

- `State`에 필요한 필드를 먼저 정의한다.
- 각 노드는 함수 하나로 만든다.
- 라우팅 노드는 가능한 JSON 출력 모델을 사용한다.
- 조건부 edge의 반환값과 mapping key를 정확히 맞춘다.
- 검색 결과 검증과 답변 검증은 별도 함수로 분리한다.
- `graph.invoke(...)` 전 `workflow.compile()`을 호출한다.
