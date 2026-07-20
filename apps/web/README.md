# apps/web — 웹 플레이그라운드

**담당: 조현찬 (입력·하이라이트 뷰 — plana 일본 학교 프로그램으로 8월 둘째주까지 부재, 팀장이 임시 대행) + imsoo ([@imsoo0816](https://github.com/imsoo0816), 결과·배치 화면)** · 상태: 🚧 입력·하이라이트 뷰 완료, 결과·배치 화면은 시작 가능

브라우저에서 텍스트를 붙여넣으면 탐지된 개인정보를 하이라이트하고 마스킹 결과를 보여주는 데모.

## 실행·테스트

```bash
cd apps/web
npm install
npm run dev      # http://localhost:5173 — 개발 서버(아래 "임시 프록시" 참고)
npm test         # vitest
npm run build    # 타입 체크 + 프로덕션 빌드
```

Node.js 24 기준 (Vite 8 / React 19 / TypeScript 7). 새 패키지 추가 전 라이선스 확인 후 [SBOM.md](../../SBOM.md)에 기록.

## ⚠️ 임시 프록시 — apps/api 완성되면 교체

`apps/api`(기태 담당)가 아직 없어서, 개발 중에는 `dev-server/scanProxyPlugin.ts`가 `/api/scan` 요청을 받아 **core CLI(`python -m maskingtape.cli --scan`)를 직접 서브프로세스로 호출**해 응답한다. 그래서 로컬에 `packages/core`가 venv에 설치돼 있어야 한다:

```bash
# 저장소 루트에서, 한 번만
python -m venv .venv
./.venv/Scripts/pip install -e packages/core   # Windows
# ./.venv/bin/pip install -e packages/core     # macOS/Linux
```

기태가 `apps/api`의 `POST /scan`을 완성하면:
1. `vite.config.ts`에서 `scanProxyPlugin()` 제거
2. `dev-server/` 폴더 삭제
3. `src/api/scanClient.ts`의 `fetch("/api/scan")`을 실제 API 주소로 변경

프론트 코드(컴포넌트·타입)는 계약(`POST /scan` 요청/응답 스키마)이 같으므로 그대로 쓴다.

## 구조

```
dev-server/
  scanProxyPlugin.ts     # 임시 개발용 프록시 (위 설명 참고 — apps/api 완성되면 삭제)
src/
  types/detection.ts     # core Detection과 1:1 (API 계약 v1 스키마) + 한국어 라벨/색상
  api/scanClient.ts       # POST /scan 호출
  lib/segments.ts         # 원문+탐지결과 → 하이라이트용 조각으로 분해 (순수 함수, 테스트 용이)
  components/
    InputPanel.tsx         # 입력·하이라이트 뷰 — 텍스트 입력 + 탐지 버튼 (조현찬 담당)
    HighlightedText.tsx     # 탐지 구간을 종류별 색상 + 라벨로 하이라이트
  App.tsx                  # 화면 조립 — imsoo가 결과·배치 화면 붙일 때 이 파일에 라우팅/탭 추가
```

- 하이라이트 색상은 5종 고정 팔레트(CVD 접근성 검증 완료, `src/index.css`의 `--kind-*` 변수) — 색만으로 구분하지 않도록 종류 라벨을 항상 텍스트로 같이 표시한다.
- 다크모드는 `prefers-color-scheme`로 자동 대응.

## 다음 (imsoo 담당 — 결과·배치 화면)

- 여러 문서를 한 번에 올려서 일괄 처리하는 화면 — `apps/desktop`의 `batch_processor.dart` 흐름을 참고하면 됨(같은 core를 쓰므로 로직은 동일, 화면만 웹으로)
- `App.tsx`에 탭 또는 라우팅을 추가해 이 화면과 입력·하이라이트 뷰를 나란히 배치
- 컴포넌트는 `src/components/` 아래 새 폴더로 분리해서 충돌 방지

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독 — 특히 §2-2(의존성 라이선스), §3(자기 파트 폴더 밖 수정 금지)
2. API 계약은 `apps/api`와 맞춘다 (`POST /scan`, `POST /anonymize`) — 계약 변경은 팀장 승인 후 `apps/api/README.md`부터 갱신
