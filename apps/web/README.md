# apps/web — 웹 플레이그라운드

**담당: plana ([@plana1470](https://github.com/plana1470), 입력·하이라이트 뷰) + imsoo ([@imsoo0816](https://github.com/imsoo0816), 결과·배치 화면)** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

브라우저에서 텍스트를 붙여넣으면 탐지된 개인정보를 하이라이트하고 마스킹 결과를 보여주는 데모.

시작할 때:

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독 — 특히 §2-2(의존성 라이선스), §3(자기 파트 폴더 밖 수정 금지)
2. 프레임워크는 두 명이 합의해서 팀장에게 공유 후 [SBOM.md](../../SBOM.md)에 추가
3. API 계약은 `apps/api`와 맞춘다 (`POST /scan`, `POST /anonymize`)
4. 화면 분담: 입력·하이라이트 뷰(plana) / 결과·배치 화면(imsoo) — 컴포넌트 폴더를 나눠서 충돌 방지
