# bench — 합성 벤치마크

**담당: seoyeon ([@seoyeon056](https://github.com/seoyeon056))** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

저작권·개인정보 걱정 없는 **자체 합성 평가 데이터셋**과 정확도(F1) 측정 스크립트. 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다.

## 규칙 (실격 사유와 직결 — 예외 없음)

- **진짜 개인정보 절대 금지** — 모든 이름·번호·주소는 생성기로 만든 합성 데이터
- **AI Hub 등 외부 데이터셋 원본 커밋 금지**(재배포 제한) — 로컬 참고용으로만 사용

## 구성

```
generator/
  entities.py    # 종류별 합성 값 생성 (name/phone/email/rrn/address)
  documents.py   # 문장 템플릿에 값을 심어 문서 + 라벨(span) 생성
generate_dataset.py  # CLI — JSONL 데이터셋 생성
evaluate.py          # CLI — core Pipeline.scan() 결과 vs 정답 → precision/recall/F1 리포트
datasets/            # 생성된 평가셋 (정답 라벨 포함)
tests/               # 생성기·평가 로직 단위 테스트
```

## 사용법

```bash
# 1. 데이터셋 생성 (재현 가능하도록 seed 고정)
python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl

# 2. core 탐지기 정확도 평가
python -m bench.evaluate bench/datasets/synth_v1.jsonl
```

현재 core의 `rrn`/`phone`/`email`/`address`는 precision/recall/F1 전부 1.0이다. `name`은 성씨 사전 +
문맥 단서(역할어·존칭) 기반 **임시 규칙판**이라 precision 0.89 / recall 0.85 정도로 낮다 — 문맥 단서가
전혀 없으면 아예 탐지하지 않도록 설계해 오탐을 줄였지만, 진짜 문맥 이해는 로컬 LLM(Ollama+Qwen) 버전이
나와야 해결된다(계획 중, `NameDetector` 교체 예정).

## 데이터셋 포맷 (생성기·평가기가 공유하는 계약)

JSONL — 한 줄에 문서 하나:

```json
{"text": "고객 홍길동 010-1234-5678 문의", "labels": [{"kind": "name", "start": 3, "end": 6}, {"kind": "phone", "start": 7, "end": 20}]}
```

- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 개인정보 원문)
- `kind`는 core의 `Detection.kind`와 동일한 문자열: `rrn`, `phone`, `email`, `name`, `address`
- 평가 기준: span 완전 일치(exact match)로 precision / recall / F1 산출
- 포맷 변경은 팀장 승인 후 이 문서부터 갱신한다
