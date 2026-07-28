# apps/web — 웹 플레이그라운드

**담당: 조현찬 (입력·하이라이트 뷰 — plana 일본 학교 프로그램으로 8월 둘째주까지 부재, 팀장이 임시 대행) + imsoo ([@imsoo0816](https://github.com/imsoo0816), 결과·배치 화면)** · 상태: 🚧 입력·하이라이트 뷰 완료, 결과·배치 화면은 시작 가능

브라우저에서 텍스트를 붙여넣으면 탐지된 개인정보를 하이라이트하고 마스킹 결과를 보여주는 데모.

## 실행·테스트

```bash
cd apps/web
npm install
npm run dev      # http://localhost:5173 — /api/*는 FastAPI 백엔드로 프록시
npm test         # vitest
npm run build    # 타입 체크 + 프로덕션 빌드
```

### 빠른 실행 순서

```bash
cd c:/MT/maskingtape
python -m venv .venv
.\.venv\Scripts\activate
pip install -e packages/core
pip install -e "apps/api[dev]"
python -m uvicorn maskingtape_api.main:app --reload --host 127.0.0.1 --port 8000
```

다른 터미널에서:

```bash
cd c:/MT/maskingtape/apps/web
npm install
npm run dev
```

> Windows PowerShell 기준으로 작성했습니다. API 서버는 http://127.0.0.1:8000, 웹 개발 서버는 http://localhost:5173 으로 실행합니다.

웹 개발 서버는 `/api/scan` 요청을 FastAPI 백엔드의 `/scan`으로 프록시합니다. 백엔드 주소를 바꿔야 하면 `VITE_API_TARGET` 환경변수를 사용합니다.

```bash
$env:VITE_API_TARGET="http://127.0.0.1:8000"
cd apps/web
npm run dev
```

Node.js 24 기준 (Vite 8 / React 19 / TypeScript 7). 새 패키지 추가 전 라이선스 확인 후 [SBOM.md](../../SBOM.md)에 기록.

## 초기 버전 대비 변경 사항

초기 웹 데모에 비해 다음 항목들을 추가·개선했습니다.

### UI/UX 개선
- 입력 영역이 텍스트 길이에 따라 자동으로 확장되며, 길어질 경우 내부 스크롤바가 생기도록 조정했습니다.
- 텍스트가 입력되면 개인정보 탐지 버튼이 “반짝이듯” 활성화되는 느낌으로 바뀌었습니다.
- 예제 버튼을 더 명확한 CTA처럼 보이도록 파란 계열 스타일로 정리했습니다.
- 탐지 결과의 개인정보 구간을 “형광펜/테이프 붙이기” 느낌의 애니메이션으로 강조했습니다.
- 결과 요약의 전화번호·이메일·주소·이름 항목을 클릭하면 해당 유형만 집중해서 볼 수 있는 필터링 기능을 추가했습니다.
- 상단 헤더와 안내 패널을 추가해 데모의 흐름이 더 자연스럽게 보이도록 구성했습니다.

### 구조 개선
- 기존의 단일 화면 구성에서 입력, 결과, 레이아웃, 도움말 컴포넌트로 역할별로 분리했습니다.
- 도움말 코치마크를 추가해 첫 사용자에게 기능 흐름을 안내할 수 있게 했습니다.
- 결과 화면을 별도 패널로 분리해 입력과 결과를 한눈에 비교하기 쉽게 만들었습니다.

### 테스트/검증
- 결과 요약과 하이라이트 렌더링에 대한 테스트를 보강했습니다.
- 빌드 검증은 `npm run build`로 확인할 수 있습니다.

## GitHub에 올리는 방법

### 1) 브랜치 생성
```bash
cd c:/MT/maskingtape
git checkout -b feat/web-ui-refresh
```

### 2) 변경 내용 확인
```bash
git status
git diff -- apps/web README.md
```

### 3) 스테이지 및 커밋
```bash
git add apps/web README.md
git commit -m "feat(web): refresh demo UI and interaction"
```

### 4) GitHub 원격 저장소에 푸시
```bash
git push -u origin feat/web-ui-refresh
```

처음 올리는 경우 원격 저장소가 아직 없다면 아래처럼 추가합니다.
```bash
git remote add origin https://github.com/<your-username>/maskingtape.git
```

### 5) GitHub에서 PR 생성
1. GitHub 저장소 페이지에서 Compare & pull request를 클릭합니다.
2. 제목과 설명을 작성합니다.
3. 예: "웹 데모 UI/UX 개선 및 결과 필터링 기능 추가"
4. Create pull request를 누르면 리뷰 요청이 완료됩니다.

## API 연동

프론트는 `src/api/scanClient.ts`에서 `POST /api/scan`을 호출합니다. 개발 중에는 `vite.config.ts`의 proxy가 이 요청을 FastAPI 백엔드 `POST /scan`으로 전달합니다. 실제 탐지와 비식별화는 `apps/api`가 `packages/core`의 `Pipeline`을 호출해 처리합니다.

## 구조

```
src/
  types/detection.ts     # core Detection과 1:1 (API 계약 v1 스키마) + 한국어 라벨/색상
  api/scanClient.ts       # POST /scan 호출
  lib/segments.ts         # 원문+탐지결과 → 하이라이트용 조각으로 분해 (순수 함수, 테스트 용이)
  lib/summary.ts          # 탐지결과 → 종류별 개수 집계 (순수 함수, 테스트 용이)
  components/
    InputPanel.tsx         # 입력 — 텍스트 입력 + 예제 프리셋 버튼 + 탐지 버튼 (조현찬 담당)
    DetectionSummary.tsx    # 탐지 요약 + 색상 범례 (종류별 건수, 0건이면 안심 메시지)
    HighlightedText.tsx     # 탐지 구간을 종류별 색상 + 라벨로 하이라이트 (확신도 낮으면 점선)
  App.tsx                  # 화면 조립 — imsoo가 결과·배치 화면 붙일 때 이 파일에 라우팅/탭 추가
```

- 하이라이트 색상은 5종 고정 팔레트(CVD 접근성 검증 완료, `src/index.css`의 `--kind-*` 변수) — 색만으로 구분하지 않도록 종류 라벨을 항상 텍스트로 같이 표시하고, 요약 바가 색상 범례를 겸한다.
- 확신도(confidence) 1.0 미만 탐지(이름·주소 등 규칙만으론 애매한 것)는 점선 밑줄로 "불확실"을 표시한다.
- 다크모드는 `prefers-color-scheme`로 자동 대응.

## 다음 (imsoo 담당 — 결과·배치 화면)

- 여러 문서를 한 번에 올려서 일괄 처리하는 화면 — `apps/desktop`의 `batch_processor.dart` 흐름을 참고하면 됨(같은 core를 쓰므로 로직은 동일, 화면만 웹으로)
- `App.tsx`에 탭 또는 라우팅을 추가해 이 화면과 입력·하이라이트 뷰를 나란히 배치
- 컴포넌트는 `src/components/` 아래 새 폴더로 분리해서 충돌 방지

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독 — 특히 §2-2(의존성 라이선스), §3(자기 파트 폴더 밖 수정 금지)
2. API 계약은 `apps/api`와 맞춘다 (`POST /scan`, `POST /anonymize`) — 계약 변경은 팀장 승인 후 `apps/api/README.md`부터 갱신
