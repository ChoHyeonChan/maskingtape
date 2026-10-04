# 이름 판정 모델 학습 (#458)

하이브리드 이름 탐지가 쓰는 로컬 LLM을 **Qwen2.5-1.5B-Instruct를 우리 합성 데이터로 파인튜닝한 모델**로
바꾸기 위한 코드다. 목표: 7B(4.7GB) 없이 1.5B(~1GB)로 같은 정확도, 문서 속 지시문(#549)에도 흔들리지 않기.

규정([#458](https://github.com/ChoHyeonChan/maskingtape/issues/458) 10/2 정리): 학습한 가중치는 **공개 저장소에
올린다**(제9조 ②항 2호 나목), 기반 모델은 Apache-2.0인 Qwen2.5 1.5B/7B만(3B·72B는 비상업), 학습 데이터는
**합성만**(KDPII·AI Hub 금지), 보고용 데이터는 학습과 **다른 템플릿**(#456).

## 흐름

```
make_dataset.py ──► data/train.jsonl (학습, 12,000건)          ┐
                ──► data/heldout_v2.jsonl (보고용 463건)        ├─ 같은 시드면 바이트 단위로 같다
                ──► data/heldout_attacks_v2.jsonl (공격 쌍 100) ┘
train_lora.py   ──► <run>/adapter (LoRA 어댑터)
export_ollama.py──► <run>/merged (공개할 가중치) ──► model-f16.gguf ──► model-q4_k_m.gguf ──► ollama `maskingtape-name:1.5b`
benchmark.py    ──► results/compare_v2.md (규칙 / 1.5B 원본 / 1.5B 학습 / 7B 비교표)
```

### 1. 데이터 (프로젝트 venv)

```powershell
python -m training.make_dataset --out-dir training/data
```

- bench 생성기 템플릿을 **번호 % 4 == 3이면 보고용**, 나머지는 학습용으로 가른다. 공격 문장은 종류마다 앞 2개 학습, 마지막 1개 보고용.
  단, 혼동어 문장 32개는 학습과 보고용이 공유한다(「평가 한계」).
- 학습 예제는 core `LLMNameDetector`가 보내는 것과 같은 대화다 — system = core의 `_SYSTEM_PROMPT` 그대로, user = 원문,
  assistant = `{"names": [...]}`(원문 표기 그대로). 그래서 **core는 모델 이름만 바꾸면 된다**.
- 구성: 이름 있는 문서 73% / 없는 문서 27%(빈 목록), 그중 공격 문장 붙은 문서 20%(정답은 그대로 → 지시문 무시 학습),
  혼동어 문장(직함+조사·지명·회사명·일반명사), 단서 없는 이름(`어제 김하늘과 갔다`).
- `train.jsonl`은 커밋하지 않는다(재현 가능). 보고용 두 파일은 커밋한다.

### 2. 학습 (학습 venv — 아래 「환경」)

```powershell
python training/train_lora.py --data training/data/train.jsonl --out <run 폴더> --batch 4 --grad-accum 4 --max-len 512 --epochs 2   # v3 설정
```

LoRA(r=16, 어텐션·MLP 전체), bf16, 2 에폭(`--epochs 2`), lr 2e-4, 정답 토큰에만 손실. RTX 3080 10GB 기준 약 35분(`--batch 4 --grad-accum 4 --max-len 512`).

### 3. Ollama 모델로 (학습 venv, Ollama 실행 중)

```powershell
python training/export_ollama.py --run D:/dev/train/runs/name-1.5b-v1 --name maskingtape-name:1.5b
maskingtape --llm --llm-model maskingtape-name:1.5b < 문서.txt
```

어댑터를 기반 모델과 합쳐(`merged/` — 허깅페이스에 올릴 가중치) llama.cpp로 f16 GGUF를 만들고, `llama-quantize`로
Q4_K_M(라이브러리 `qwen2.5:1.5b`와 같은 양자화, 986MB)으로 줄인 뒤 `ollama create`로 등록한다. Ollama 자체의
`create -q`는 safetensors 경로만 지원하고 그 경로가 Qwen2를 아직 못 받아서(직접 확인) 쓰지 않는다.

### 4. 비교표 (프로젝트 venv, Ollama 실행 중)

```powershell
python -m training.benchmark --models qwen2.5:1.5b maskingtape-name:1.5b qwen2.5:7b --out training/results/compare_v2.md
```

bench의 채점기(`compare_name_detectors`, `evaluate_attacks`)를 그대로 써서 모델마다 **LLM 단독**(모델 자체 실력)과
**하이브리드**(제품 구성)의 이름 P/R/F1, 공격 판 재현율, 문서당 시간, 크기를 낸다.

## 환경 (학습 전용 venv — 프로젝트 venv와 분리)

```powershell
# D:\dev\train\venv — 개발 도구라 SBOM 본문 대상이 아니다(배포물에 들어가지 않음)
py -3.10 -m venv D:\dev\train\venv
D:\dev\train\venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu124   # BSD-3
D:\dev\train\venv\Scripts\pip install transformers peft accelerate huggingface_hub gguf          # Apache-2.0 / MIT(gguf)
git clone --depth 1 https://github.com/ggml-org/llama.cpp D:\dev\llama.cpp                       # MIT — GGUF 변환 스크립트
gh release download b11368 --repo ggml-org/llama.cpp --pattern "*bin-win-cpu-x64.zip" --dir D:\dev\llama.cpp-bin  # llama-quantize.exe (zip 풀기)
$env:HF_HOME = "D:\dev\hf_cache"
```

확인한 판: torch 2.6.0+cu124, transformers 5.18.0, peft 0.21.2, gguf 0.19.0 (2026-10-03).

## 결과 (2026-10-03, `results/compare_v2.md` — 보고용 v2 세트)

보고용 세트(학습에 안 쓴 템플릿·공격 문장, 이름 뒤 조사 교정본) 이름 F1 — `LLM 단독 / 하이브리드`, 괄호는 오탐:

| 모델 | 크기 | 보고용 F1 | synth_v1 F1 | 문서당 | 공격 판 재현율(단독) |
|---|---|---|---|---|---|
| 규칙 전용 | — | — / 0.801 (22) | 0.949 | 0 ms | — |
| qwen2.5:1.5b 원본 | 986 MB | 0.626 (130) / 0.786 (타임아웃 1) | 0.714 / 0.827 | 174 ms | 0.28 |
| maskingtape-name-1.5b v2 | 986 MB | 0.946 (44) / 0.913 | 0.983 / 0.953 | 94 ms | 0.99 |
| **maskingtape-name-1.5b v3 (채택)** | 986 MB | **0.978 (13) / 0.944** | **0.994 / 0.962** | 111 ms | **1.00** |
| qwen2.5:7b | 4,683 MB | 0.920 (41) / 0.907 | 0.926 / 0.945 | 134 ms | 0.41 |

- 이 보고용 세트에서 v3는 단독·하이브리드 모두 7B보다 높다(0.978 > 0.920, 0.944 > 0.907). 단독 기준으로 오탐이 규칙 전용보다 적고(13 < 22) 지시문 공격 5종 재현율이 1.00이다. 크기는 1/5. **아래 「평가 한계」를 함께 읽는다 — 외부 데이터에서는 재현율이 7B와 같다.**
- v2 → v3: 보고용 오류의 절반이 생성기 템플릿의 **틀린 조사**(`{name}은` → "서아은") 때문이었다. 렌더 뒤 이름 라벨 다음 조사를 받침에 맞게 고치고(`fix_josa`), 직함+업무어 부정 문장(보고용 단어는 뺌)을 보태 2 에폭 학습. "팀장 안내가" 모양은 학습에 없는데 그 오탐 14건이 0이 됐다(단어 "안내" 자체는 다른 문장으로 학습 244건에 있다).
- 보고용 v1(교정 전) 세트의 1·2차 결과는 `results/compare.md`에 남겨 둔다. 원본 1.5B는 한 문서에서 JSON을 끝맺지 못하고 타임아웃 — 벤치는 문서 단위 실패를 세고 빈 결과로 처리한다.
- 남은 오류: `박인도`(박인 + 도)처럼 받침 있는 2음절 이름 + 조사 경계가 대부분.
- 학습 중 VRAM 캐시 조각으로 10배 느려지는 문제(Windows는 `expandable_segments` 미지원) → `train_lora.py`가 VRAM 상한 85%·50스텝마다 캐시 반환으로 막는다.

### 이 수치를 읽을 때 — 평가 한계

보고용 세트는 **학습과 같은 생성기**로 만든 것이라 학습 분포 안쪽 평가다. 아래를 감안해 읽는다.

- **혼동어 문장을 학습과 보고용이 공유한다.** `_CONFUSER_SENTENCES` 32문장이 양쪽에 다 들어간다(학습 전용 추가분 56문장은
  학습에만). 보고용 463건 중 **172건**이 이 문장을 포함하고, 그중 **44건**은 그 문장 하나뿐이라 학습 문서와 글자까지 같다.
  "보고용은 학습에 들어가지 않는다"는 문장 틀과 공격 문장에만 해당한다. 그래서 보고용 수치, 특히 **오탐은 낙관적**일 수 있다.
- **이름 풀이 같다.** 보고용 이름 566개가 모두 학습과 같은 풀(성 30개 · 음절 32개)에서 나오고, 2음절 이름 284개는 전부
  학습 정답에 같은 문자열로 있다.
- **v2·v3 데이터는 보고용 오류를 보고 고쳤다**(생활어 혼동어, 조사 교정, 직함+업무어). 보고용에 맞춰진 면이 있다.
- **synth_v1은 참고값이다.** 500건 중 303건에 학습에 쓴 문장 틀이 들어 있다.
- **단독과 하이브리드를 구분해 읽는다.** "오탐이 규칙 전용보다 적다(13 < 22)"와 "공격 재현율 1.00 대 0.41"은 **LLM 단독** 기준이다.
  제품 구성인 **하이브리드**는 오탐 32(규칙 22 · 7B 59), 공격 판 재현율 0.95 대 7B 0.93이다.
- **학습에 쓰지 않은 외부 데이터에서는 7B와 재현율이 같다.** KDPII test에서 뽑은 500문장(이름 177개)으로 하이브리드를 재면
  재현율은 둘 다 0.825, 정밀도는 7B가 높다(0.527 대 0.471, 오탐 131 대 164). 1.5B는 크기 1/5에 약 3배 빠르다. 그래서 정직한
  요약은 "7B보다 정확하다"가 아니라 **"재현율은 같고, 더 작고 빠르며, 문서 속 지시문에 덜 흔들린다"** 이다. 측정 조건과 출처는
  저장소 루트 README의 정확도 절(#645)과 SBOM 부록 D에 있다.
