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

```bash
git clone https://github.com/ChoHyeonChan/maskingtape.git
cd maskingtape
python -m venv .venv
# Windows: .venv\Scripts\activate / macOS·Linux: source .venv/bin/activate
pip install -e "packages/core[dev]"

maskingtape "주민번호 800101-1234560 문의주세요"
# → 주민번호 ************** 문의주세요

maskingtape --scan "주민번호 800101-1234560 문의주세요"   # 탐지 리포트(JSON)만
pytest packages/core                                       # 테스트
```

라이브러리로 쓰기:

```python
from maskingtape import Pipeline

result = Pipeline().anonymize("주민번호 800101-1234560 문의주세요")
print(result.text)         # 주민번호 ************** 문의주세요
print(result.detections)   # [Detection(kind='rrn', start=5, end=19, ...)]
```

※ 예시의 주민등록번호는 체크섬만 맞춘 **합성 번호**다.

## 저장소 구조

| 경로 | 내용 | 담당 |
|---|---|---|
| `packages/core/` | Python 탐지·마스킹 엔진 + CLI (순수 로직) | 조현찬 |
| `packages/mcp-server/` | MCP 서버 — core를 에이전트 도구로 노출 | 조현찬 |
| `apps/api/` | FastAPI 백엔드 — 웹·데스크톱 공용 | 풀스택 |
| `apps/web/` | 웹 플레이그라운드 (탐지 하이라이트 데모) | 프론트 ×2 |
| `apps/desktop/` | Flutter 데스크톱 앱 (드래그&드롭 배치 처리) | Flutter |
| `bench/` | 합성 벤치마크 데이터 + F1 정확도 리포트 | 데이터 |

## 팀원이 개발 시작하기 전에

1. 루트의 **[CLAUDE.md](CLAUDE.md) 필독** — 대회 규정에서 나온 규칙이라 위반하면 팀 전체가 실격될 수 있다
2. 자기 파트 폴더의 README 확인
3. **코드 시작은 스켈레톤 머지 후 팀장 신호에 따라** — 의존성 추가 전 [SBOM.md](SBOM.md) 규칙 확인

## 라이선스

[Apache-2.0](LICENSE). 사용한 모든 의존성의 출처·라이선스는 [SBOM.md](SBOM.md)에 기록한다.
