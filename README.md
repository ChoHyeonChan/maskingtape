# 마스킹테이프 maskingtape

> 한국어 개인정보 비식별화 오픈소스 엔진 — 규칙 기반 탐지 + 로컬 LLM 문맥 판단 하이브리드

한국어 문서·데이터셋에서 개인정보(주민등록번호·전화번호·주소·이름 등)를 탐지해 마스킹·가명처리하는 **Python 라이브러리 + CLI + MCP 서버**.
AI 에이전트가 한국어 데이터를 다루기 전에 거치는 **프라이버시 계층**을 목표로 한다.

**2026 오픈소스 개발자대회**(과학기술정보통신부 주최·NIPA 주관) 출품작 — 팀 **마스킹테이프** · Apache-2.0

## 왜 maskingtape인가

- **한국어 전용**: 주민등록번호(체크섬 검증 포함)·한국 전화번호·도로명 주소·한국어 이름 등 국내 포맷 특화 — 영어권 도구(Presidio 등)가 못 채우는 갭
- **하이브리드 탐지**: 정규식·사전 규칙(빠름, 결정적) + 로컬 LLM 문맥 판단(인명 vs 상호명 구분 같은 애매한 케이스, 선택 사항)
- **완전 로컬**: 외부 API 호출 없음. LLM도 Ollama 기반 오픈웨이트 모델만 사용 — 개인정보가 밖으로 나가지 않는다
- **규칙 전용 모드**: LLM 없이도 동작 — 저사양 환경에서도 쓸 수 있다
- **MCP 서버**: AI 에이전트 워크플로에 비식별화 계층을 끼워 넣을 수 있다

## 빠른 시작 (개발 중 — API는 바뀔 수 있음)

**필요한 것: Python 3.10 이상.** 그게 전부다 — 코어 엔진과 CLI는 표준 라이브러리만 쓰고, 외부 서비스도 부르지 않는다. (로컬 LLM 기능은 선택 사항이며 설치 방법은 [packages/core](packages/core)에 있다. 웹 데모는 Node.js 20+, 데스크톱 앱은 Flutter가 추가로 필요하며 각 폴더 README를 참고한다.)

```bash
git clone https://github.com/ChoHyeonChan/maskingtape.git
cd maskingtape
python -m venv .venv
# Windows: .venv\Scripts\activate / macOS·Linux: source .venv/bin/activate
pip install -e "packages/core[dev]"

maskingtape "주민번호 800101-1234560 문의주세요"
# → 주민번호 ************** 문의주세요

maskingtape --strategy label "연락처 010-1234-5678"        # → 연락처 [전화번호]
maskingtape --scan "주민번호 800101-1234560 문의주세요"   # 탐지 리포트(JSON)만
pytest packages/core                                       # 테스트
```

현재 탐지: **주민등록번호**(체크섬 검증), **전화번호**(휴대폰·유선·070, +82 표기), **이메일**, **주소**(행정구역), **이름**(규칙 + 로컬 LLM 문맥 판단)

라이브러리로 쓰기:

```python
from maskingtape import Pipeline

result = Pipeline().anonymize("주민번호 800101-1234560 문의주세요")
print(result.text)         # 주민번호 ************** 문의주세요
print(result.detections)   # [Detection(kind='rrn', start=5, end=19, ...)]
```

※ 예시의 주민등록번호는 체크섬만 맞춘 **합성 번호**다.

## 정확도 (공개 벤치마크)

저작권·개인정보 걱정 없는 **자체 합성 데이터셋**으로 정확도를 측정한다 — 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다. 아무나 다음 한 줄로 재현할 수 있다:

```bash
python -m bench.evaluate bench/datasets/synth_v1.jsonl
```

합성 데이터셋(500건)도 시드로 고정돼 있어 바이트 단위로 똑같이 재생성된다 — `python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl`

**측정 기준: `main` 브랜치 `79bb4aa` · 규칙 전용 모드(LLM 미사용)**

| 종류 | precision | recall | F1 |
|---|---|---|---|
| 주민등록번호 | 1.000 | 1.000 | 1.000 |
| 전화번호 | 1.000 | 1.000 | 1.000 |
| 이메일 | 1.000 | 1.000 | 1.000 |
| 이름 (규칙 전용) | 0.894 | 0.553 | 0.683 |
| 주소 | 0.371 | 0.371 | 0.371 |
| **전체** | **0.907** | **0.770** | **0.833** |

번호(주민등록번호·전화번호·이메일)는 형태와 체크섬으로 완전히 잡힌다. 나머지 둘은 **고치는 중이고, 무엇이 왜 부족한지 숫자로 공개한다**:

- **주소** — 도로명 주소(`월드컵로237길 49 ...`)와 4단계 행정구역(`수원시 영통구 ...`)에서 구간이 잘려 span 불일치가 난다. 수정 진행 중: [#66](https://github.com/ChoHyeonChan/maskingtape/issues/66)
- **이름 (recall 0.553)** — 한국어 이름은 형태만으로 구분되지 않아 규칙만으로는 문맥 없는 이름을 놓친다. 이것이 **로컬 LLM 하이브리드**(`--llm`)가 필요한 이유이고, 그 효과는 [#46](https://github.com/ChoHyeonChan/maskingtape/issues/46)에서 같은 데이터셋으로 비교 측정한다.

> 신용카드번호 탐지기는 이 표에 없다 — 합성 데이터셋 생성기가 아직 카드번호를 만들지 않아 측정 대상이 아니다([#73](https://github.com/ChoHyeonChan/maskingtape/issues/73)). 탐지기 자체는 Luhn 체크섬 검증과 단위 테스트로 검증돼 있다.

마스킹 결과에 개인정보가 실제로 남는지도 따로 측정한다 — `python -m bench.evaluate_masking bench/datasets/synth_v1.jsonl`. 상세는 [bench/](bench/) 참고.

## MCP 서버로 쓰기 (AI 에이전트용)

에이전트가 한국어 데이터를 외부로 보내기 전에 자동으로 비식별화하는 프라이버시 계층:

```bash
pip install -e packages/core -e packages/mcp-server
claude mcp add maskingtape -- maskingtape-mcp      # Claude Code 등록
```

제공 도구: `scan_text`(탐지 리포트), `anonymize_text`(mask/label 비식별화), `anonymize_file`(로컬 파일을 통째로 비식별화해 사본 저장). 상세: [packages/mcp-server](packages/mcp-server)

## 저장소 구조

모든 탐지·마스킹 로직은 `packages/core` **하나**에 있고, 나머지는 그걸 감싸 쓴다 — 탐지기를 한 번 고치면 모든 표면(CLI·MCP·API·앱)이 함께 좋아진다.

```mermaid
flowchart TD
    core["packages/core: 탐지·마스킹 엔진"]
    core --> cli["CLI: maskingtape 명령"]
    core --> mcp["packages/mcp-server: MCP 서버"]
    core --> api["apps/api: REST API"]
    api --> web["apps/web: 웹 플레이그라운드"]
    api --> desktop["apps/desktop: 데스크톱 앱"]
    bench["bench: 합성 벤치마크"] -.->|정확도 측정| core
```

> 웹·데스크톱은 통합 전까지 `apps/api` 대신 core CLI를 직접 호출한다(같은 엔진).

| 경로 | 내용 | 담당 |
|---|---|---|
| `packages/core/` | Python 탐지·마스킹 엔진 + CLI (순수 로직) | 조현찬 |
| `packages/mcp-server/` | MCP 서버 — core를 에이전트 도구로 노출 | 조현찬 |
| `apps/api/` | FastAPI 백엔드 — 웹·데스크톱 공용 | 풀스택 |
| `apps/web/` | 웹 플레이그라운드 (탐지 하이라이트 데모) | 프론트 ×2 |
| `apps/desktop/` | Flutter 데스크톱 앱 (드래그&드롭 배치 처리) | Flutter |
| `bench/` | 합성 벤치마크 데이터 + F1 정확도 리포트 | 데이터 |

## 개발에 참여하기

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — 협업 규칙 (이슈 → 브랜치 → PR → 머지). AI로 작업한다면 이 파일부터 읽히세요.
- **[ROADMAP.md](ROADMAP.md)** — 개발 계획과 현재 정확도
- **[CLAUDE.md](CLAUDE.md)** — 대회 규정에서 나온 필수 규칙 (위반 시 팀 전체 실격)
- 진행 상황: [Issues](https://github.com/ChoHyeonChan/maskingtape/issues) · [Milestones](https://github.com/ChoHyeonChan/maskingtape/milestones)
- 의존성을 추가할 땐 같은 PR에서 [SBOM.md](SBOM.md)를 갱신합니다.

## 라이선스

[Apache-2.0](LICENSE). 사용한 모든 의존성의 출처·라이선스는 [SBOM.md](SBOM.md)에 기록한다.
