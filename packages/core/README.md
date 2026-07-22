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

- detectors: `rrn.py`(주민등록번호), `phone.py`(휴대폰·유선·070), `email.py`, `address.py`(행정구역 주소), `name.py`(이름 — 규칙판), `name_llm.py`(이름 — 로컬 LLM 문맥 판단, **선택**)
- anonymizers: `mask.py`(*로 가림), `label.py`([전화번호] 식 라벨 치환, 번호 매기기 지원)

## 이름 탐지: 규칙판 vs LLM판

기본(`default_detectors()`)은 **규칙판**이라 아무 설치 없이 동작한다. 다만 성씨 사전에 의존해서
역할어 뒤에 오는 일반 단어를 오탐할 수 있다("작성자 **정보**"의 정+보, "고객 **지원**"의 지+원).

문맥까지 보려면 **로컬 Ollama**를 띄우고 `--llm`을 준다 (외부 API 호출 없음 — 대회 규정 §2-3):

```bash
ollama pull qwen2.5:7b       # Apache-2.0 (Qwen2.5는 3B·72B만 비상업 제한이라 7B를 쓴다)
maskingtape --llm --strategy label "작성자 정보 참고: 최지훈 담당자(010-1234-5678)"
# → 작성자 정보 참고: [이름] 담당자([전화번호])   ← '정보'는 오탐하지 않고 '최지훈'만 잡는다
```

- Ollama가 없으면 `--llm`은 무엇을 설치·실행해야 하는지 알려주고 종료한다(조용히 실패하지 않음).
- `--llm-model`로 다른 로컬 모델을 지정할 수 있다.
- LLM판은 `default_detectors()`에 **넣지 않는다** — Ollama 없는 환경(CI·다른 팀원 PC)에서 깨지면 안 되므로 `llm_detectors()`/`--llm`으로 명시 선택할 때만 쓴다.

## 예정 (코어 v2)

- anonymizers: `pseudonym.py`(가명처리), `hash.py`
