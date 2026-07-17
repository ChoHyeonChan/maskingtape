# bench — 합성 벤치마크

**담당: 데이터 담당** · 상태: ⏳ 스켈레톤 머지 후 시작

저작권·개인정보 걱정 없는 **자체 합성 평가 데이터셋**과 정확도(F1) 측정 스크립트. 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다.

## 규칙 (실격 사유와 직결 — 예외 없음)

- **진짜 개인정보 절대 금지** — 모든 이름·번호·주소는 생성기로 만든 합성 데이터
- **AI Hub 등 외부 데이터셋 원본 커밋 금지**(재배포 제한) — 로컬 참고용으로만 사용

## 구성 예정

```
generator/     # 합성 문서 생성기 (이름·번호·주소를 만들어 문장에 심는다)
datasets/      # 생성된 평가셋 (정답 라벨 포함)
evaluate.py    # 탐지 결과 vs 정답 → precision/recall/F1 리포트
```

## 데이터셋 포맷 (생성기·평가기가 공유하는 계약)

JSONL — 한 줄에 문서 하나:

```json
{"text": "고객 홍길동 010-1234-5678 문의", "labels": [{"kind": "name", "start": 3, "end": 6}, {"kind": "phone", "start": 7, "end": 20}]}
```

- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 개인정보 원문)
- `kind`는 core의 `Detection.kind`와 동일한 문자열: `rrn`, `phone`, `email`, `name`, `address`
- 평가 기준: span 완전 일치(exact match)로 precision / recall / F1 산출
- 포맷 변경은 팀장 승인 후 이 문서부터 갱신한다
