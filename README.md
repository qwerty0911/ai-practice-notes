# AI Engineering Practice Notes

AI 교육 실습 내용을 정리한 저장소입니다. 원본 실습 노트북은 `notebooks/`에 보관하고, 핵심 개념과 자주 쓰는 코드 패턴은 `notes/`에 요약했습니다.

## 구성

- `notebooks/`: 교육 실습 Jupyter Notebook 원본
- `notes/01_models_and_training.md`: 모델 종류, 토크나이저, 추론, 파인튜닝, SFT/DPO, LoRA/양자화 정리
- `notes/02_api_fastapi_streaming.md`: OpenAI API 호출, FastAPI 서버, 스트리밍 응답 정리
- `notes/03_langchain_langgraph.md`: LangChain 구성 요소와 LangGraph 노드/엣지 단위 정리
- `notes/04_advanced_rag_search.md`: 청킹, 검색 품질 진단, 하이브리드 검색, 쿼리 변환, 리랭킹 정리
- `notes/notebook_index.md`: 주차/일차별 노트북 목록

## 학습 흐름

1. Hugging Face 기본기
   - Tokenizer, Pipeline API, AutoModel, generate, attention mask, KV cache
   - 커스텀 모델 헤드, Dataset 전처리, Trainer API, evaluate

2. 모델 학습과 최적화
   - Supervised Fine-Tuning(SFT)
   - Direct Preference Optimization(DPO)
   - LoRA/PEFT, 4bit quantization, checkpoint, Hugging Face Hub 배포
   - 이미지 캡셔닝 모델 fine-tuning

3. API 서버 구현
   - OpenAI 호환 API 호출
   - FastAPI 기반 `/chat` 엔드포인트
   - streaming 응답, async generator, 오류 처리

4. LangChain, RAG, LangGraph
   - Prompt, LLM, DocumentLoader, OutputParser, Chain
   - PDF/엑셀/웹 데이터 기반 RAG
   - Vector DB 캐싱, chat history, Self-RAG, Adaptive RAG
   - LangGraph의 `State`, node function, edge, conditional edge 구성

5. Advanced RAG Search
   - chunk size/overlap 조정과 검색 품질 진단
   - 한국어 임베딩 모델 비교와 `top_k` 튜닝
   - BM25 + Vector hybrid search, RRF 융합
   - Multi-Query, HyDE 기반 query transformation
   - Cross-Encoder reranking과 모듈러 RAG 파이프라인

## 실행 환경

노트북별로 필요한 패키지가 조금씩 다릅니다. 기본 패키지는 아래처럼 설치할 수 있습니다.

```bash
pip install -r requirements.txt
```

API 실습은 `.env`에 API 키와 모델 정보를 넣어서 실행합니다.

```env
OPENAI_API_KEY=...
MLAPI_MODEL=openai/gpt-5o-mini
```

로컬 LLM 실습은 Ollama 모델이 필요할 수 있습니다.

```bash
ollama pull llama3.1
ollama pull llama3.2:3B
```

## 빠른 참고

- 분류 모델: `AutoModelForSequenceClassification`
- 생성 모델: `AutoModelForCausalLM`
- 멀티모달 이미지 캡셔닝: `VisionEncoderDecoderModel`
- 학습 루프: `Trainer`, `SFTTrainer`, `DPOTrainer`, `Seq2SeqTrainer`
- 경량 학습: `LoraConfig`, `BitsAndBytesConfig`
- LangChain 기본 체인: `prompt | llm | parser`
- RAG 체인: `retriever -> context -> prompt -> llm -> parser`
- Hybrid Search: `BM25 + Vector -> RRF -> rerank`
- Advanced RAG: `multi-query -> hybrid search -> rerank -> generate`
- LangGraph 기본 구조: `StateGraph(State) -> add_node -> add_edge/add_conditional_edges -> compile`
