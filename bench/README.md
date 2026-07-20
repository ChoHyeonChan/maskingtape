# bench — 합성 벤치마크

**담당: seoyeon ([@seoyeon056](https://github.com/seoyeon056))** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

저작권·개인정보 걱정 없는 **자체 합성 평가 데이터셋**과 정확도(F1) 측정 스크립트. 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다.

## 규칙 (실격 사유와 직결 — 예외 없음)

- **진짜 개인정보 절대 금지** — 모든 이름·번호·주소는 생성기로 만든 합성 데이터
- **AI Hub 등 외부 데이터셋 원본 커밋 금지**(재배포 제한) — 로컬 참고용으로만 사용

## 구성

```
generator/
  entities.py     # 종류별 합성 값 생성 (name/phone/email/rrn/address)
  distractors.py  # 개인정보가 아닌 '헷갈리는' 값 생성 (오탐 측정용)
  documents.py    # 문장 템플릿에 값을 심어 문서 + 라벨(span) 생성
generate_dataset.py  # CLI — JSONL 데이터셋 생성
evaluate.py          # CLI — core Pipeline.scan() 결과 vs 정답 → precision/recall/F1 리포트
datasets/            # 생성된 평가셋 (정답 라벨 포함)
tests/               # 생성기·평가 로직 단위 테스트
```

## 사용법

```bash
# 1. 데이터셋 생성 (재현 가능하도록 seed 고정, 기본 25%는 오탐 측정용 무-개인정보 문서)
python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl

# 2. core 탐지기 정확도 평가
python -m bench.evaluate bench/datasets/synth_v1.jsonl
```

현재 core에는 `rrn`/`phone`/`email` 탐지기만 있어 `name`/`address`는 recall 0으로 나온다 —
이는 생성기 버그가 아니라 아직 구현되지 않은 탐지기를 정확히 반영하는 결과다.

## 오탐(False Positive) 측정

기존에는 데이터셋 전체가 "개인정보가 있는 문서"뿐이라 재현율(recall)만 측정 가능했고,
core가 개인정보 아닌 걸 잘못 잡아내는지(정밀도, precision)는 검증 불가능했다.

`generator/distractors.py`가 주문번호·사업자등록번호·날짜·가격처럼 숫자가 섞여 있지만
개인정보는 아닌 값과, 지역번호·생년월일이 실제로는 존재하지 않는 '전화번호/주민번호 모양'
값을 만든다. `--negative-ratio`(기본 0.25)만큼의 문서는 정답 라벨이 0개인 채로 생성되고,
core가 여기서 뭔가를 탐지하면 `evaluate.py`가 그대로 FP로 집계한다.

## 문장·표기 다양성

실제 문서는 같은 개인정보라도 표기 형식이 제각각이라, 생성기도 그 다양성을 반영한다:

- **전화번호**: 하이픈(`010-1234-5678`)뿐 아니라 점(`.`)·공백·구분자 없음(`01012345678`)·
  `+82` 국제표기까지 core가 허용하는 형식을 무작위로 섞는다
- **주민번호**: 하이픈/공백/구분자 없음, 1900·2000년대 성별코드를 모두 커버
- **주소**: 지번 주소(`강남구 역삼동 12-3`)와 도로명 주소(`테헤란로12길 3`, 아파트 동/호 포함)를 섞는다
- **이름**: 성씨 30종 × 이름 음절 30종 조합, 통계청 다빈도 성씨 기준(특정 인물 아님)
- **문장 맥락**: 고객센터/병원/학교/관공서/인사/배송/금융 등 10여 개 업무 시나리오, 한 문서에
  같은 종류 개인정보가 두 번 등장하는 경우(담당자 교체, 자택/직장 번호 등)도 포함

## 데이터셋 포맷 (생성기·평가기가 공유하는 계약)

JSONL — 한 줄에 문서 하나:

```json
{"text": "고객 홍길동 010-1234-5678 문의", "labels": [{"kind": "name", "start": 3, "end": 6}, {"kind": "phone", "start": 7, "end": 20}]}
```

- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 개인정보 원문)
- `kind`는 core의 `Detection.kind`와 동일한 문자열: `rrn`, `phone`, `email`, `name`, `address`
- 평가 기준: span 완전 일치(exact match)로 precision / recall / F1 산출
- 포맷 변경은 팀장 승인 후 이 문서부터 갱신한다
