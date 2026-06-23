# 모델 종류와 학습 과정 정리

## 모델 종류

### Tokenizer

텍스트를 모델 입력 토큰으로 바꾸는 구성 요소입니다. 실습에서는 `AutoTokenizer.from_pretrained(...)`를 사용했습니다.

```python
from transformers import AutoTokenizer

model_name = "bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
```

주요 파라미터:

- `padding`: 배치 내 길이를 맞춤
- `truncation`: 최대 길이를 넘는 입력을 자름
- `max_length`: 입력 최대 토큰 길이
- `return_offsets_mapping`: 원문 문자 위치와 토큰 위치를 연결
- `return_tensors="pt"`: PyTorch Tensor로 반환

### Pipeline API

가장 빠르게 추론을 확인할 때 사용합니다. 모델 로드, 토크나이징, 후처리를 한 번에 처리합니다.

```python
from transformers import pipeline

model_name = "HuggingFaceTB/SmolLM2-135M-Instruct"
pipe = pipeline("text-generation", model=model_name, tokenizer=model_name)
```

### AutoModel 계열

모델 목적에 따라 클래스를 다르게 씁니다.

- `AutoModel`: backbone hidden state가 필요할 때
- `AutoModelForCausalLM`: 다음 토큰 생성, 챗봇, SFT/DPO
- `AutoModelForSequenceClassification`: 분류 태스크
- `VisionEncoderDecoderModel`: 이미지 입력을 텍스트로 생성하는 image captioning

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

checkpoint = "HuggingFaceTB/SmolLM2-135M-Instruct"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForCausalLM.from_pretrained(checkpoint)
```

## 추론과 generate

생성 모델은 `generate()`에서 출력 길이와 샘플링 방식을 조절합니다.

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    do_sample=True,
    temperature=0.7,
    top_k=50,
)
```

주요 파라미터:

- `max_new_tokens`: 새로 생성할 토큰 수
- `do_sample`: 확률 샘플링 사용 여부
- `temperature`: 분포를 부드럽게 하거나 날카롭게 조절
- `top_k`, `top_p`: 후보 토큰 제한
- `attention_mask`: padding 위치를 무시하도록 지정
- `use_cache`: KV cache 사용으로 반복 생성 속도 개선

## Trainer API

Hugging Face `Trainer`는 학습 루프를 직접 작성하지 않고도 학습, 평가, 저장을 처리합니다.

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./tmp/hf_trainer_practice",
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=1,
    learning_rate=5e-5,
    logging_steps=1,
    save_strategy="epoch",
    report_to="none",
)
```

실습 흐름:

1. 데이터셋 준비
2. 토크나이징 함수 작성
3. `DataCollatorWithPadding`으로 배치 구성
4. `compute_metrics`로 평가 지표 정의
5. `TrainingArguments`와 `Trainer` 연결
6. `trainer.train()`, `trainer.evaluate()` 실행

## SFT

SFT는 정답 응답이 있는 instruction 데이터로 생성 모델을 지도학습하는 단계입니다.

실습 모델:

- `meta-llama/Llama-3.2-1B-Instruct`

핵심 구성:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
import torch

model_name = "meta-llama/Llama-3.2-1B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
)

peft_config = LoraConfig(
    r=16,
    lora_alpha=16,
    lora_dropout=0.1,
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

training_args = SFTConfig(
    output_dir="outputs/sft_model",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=1,
    num_train_epochs=2,
    learning_rate=2e-5,
    bf16=True,
    logging_steps=10,
    save_total_limit=2,
    max_seq_length=1024,
    optim="paged_adamw_32bit",
)
```

체크 포인트:

- 입력은 instruction prompt 형식으로 정리
- 길이가 너무 긴 샘플은 `max_seq_length` 기준으로 필터링
- 작은 GPU 환경에서는 4bit quantization과 LoRA를 같이 사용

## DPO

DPO는 선호 데이터에서 `chosen` 응답과 `rejected` 응답을 비교해 모델을 정렬하는 학습입니다.

핵심 구성:

```python
from trl import DPOTrainer, DPOConfig

training_args = DPOConfig(
    output_dir="outputs/dpo_model",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    num_train_epochs=2,
    max_grad_norm=0.3,
    learning_rate=1e-6,
    bf16=True,
    logging_steps=10,
    optim="paged_adamw_32bit",
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    remove_unused_columns=True,
    max_prompt_length=512,
    max_length=1024,
    save_strategy="epoch",
    beta=0.2,
)
```

중요 포인트:

- DPO의 학습률은 SFT보다 작게 잡는 편
- `beta`는 선호/비선호 간 차이를 얼마나 강하게 반영할지 결정
- `prompt`, `chosen`, `rejected` 형태로 데이터셋을 맞춰야 함

## LoRA와 4bit 양자화

LoRA는 전체 모델을 업데이트하지 않고 일부 projection layer에 작은 학습 파라미터를 붙입니다.

- `r`: LoRA rank
- `lora_alpha`: LoRA 출력 스케일
- `lora_dropout`: 과적합 방지
- `target_modules`: LoRA를 붙일 모듈

4bit quantization은 모델 메모리를 줄여 작은 GPU에서도 로드 가능하게 합니다.

- `load_in_4bit=True`
- `bnb_4bit_compute_dtype=torch.bfloat16`

## Image Captioning Fine-Tuning

이미지를 입력으로 받고 텍스트 캡션을 생성하는 seq2seq 구조입니다.

```python
from transformers import VisionEncoderDecoderModel
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

training_args = Seq2SeqTrainingArguments(
    output_dir="VIT_large_gpt2",
    per_device_train_batch_size=CFG.TRAIN_BATCH_SIZE,
    per_device_eval_batch_size=CFG.VAL_BATCH_SIZE,
    predict_with_generate=True,
    evaluation_strategy="epoch",
    do_train=True,
    do_eval=True,
    logging_steps=1024,
    save_steps=2048,
    warmup_steps=1024,
    learning_rate=CFG.LR,
    max_steps=1500,
    num_train_epochs=CFG.EPOCHS,
    overwrite_output_dir=True,
    save_total_limit=1,
)
```

흐름:

1. 이미지 feature extractor 준비
2. caption tokenizer 준비
3. image-caption dataset 구성
4. `VisionEncoderDecoderModel` 로드
5. `Seq2SeqTrainer`로 학습
6. `predict_with_generate=True`로 생성 기반 평가
