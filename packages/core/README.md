# packages/core — 코어 엔진

**담당: 조현찬 (팀장)**

한국어 개인정보 탐지·마스킹의 모든 로직이 여기 있다. **순수 로직만** — UI·네트워크 코드 금지, `apps/`를 import하지 않는다.

## 구조

```
maskingtape/
  types.py        # Detection 공용 타입 — 탐지기와 마스킹기가 이걸로 대화한다
  pipeline.py     # 탐지기 + 마스킹 전략 조립 (조립만, 로직 없음)
  cli.py          # 명령줄 도구
  detectors/      # 탐지기 1종 = 파일 1개 — rrn.py가 참고 구현
  anonymizers/    # 마스킹 전략 1종 = 파일 1개 — mask.py가 참고 구현
tests/            # 합성 데이터로만 테스트 (진짜 개인정보 금지)
```

## 개발

```bash
# 레포 루트에서
python -m venv .venv
# Windows: .venv\Scripts\activate / macOS·Linux: source .venv/bin/activate
pip install -e "packages/core[dev]"
pytest packages/core        # 테스트
ruff check packages/core    # 린트
```

## 새 탐지기 추가하는 법

1. `maskingtape/detectors/`에 파일 하나 추가 (예: `phone.py`) — `rrn.py` 패턴을 따른다
2. `Detector` 상속, `kind` 지정, `detect()` 구현
3. `detectors/__init__.py`의 `default_detectors()`에 등록
4. `tests/`에 합성 데이터 테스트 추가

## 현재 구현

- detectors: `rrn.py`(주민등록번호), `phone.py`(휴대폰·유선·070), `email.py`
- anonymizers: `mask.py`(*로 가림), `label.py`([전화번호] 식 라벨 치환, 번호 매기기 지원)

## 예정 (코어 v2)

- detectors: `address.py`(도로명 주소), `name_llm.py`(로컬 LLM 문맥 판단 — 인명 vs 상호명)
- anonymizers: `pseudonym.py`(가명처리), `hash.py`
