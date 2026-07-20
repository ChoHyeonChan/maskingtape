# apps/desktop — Flutter 데스크톱 앱

**담당: 김준형** · 상태: 🚧 core CLI 연동 완료 (드롭 → 일괄 비식별화 → `_masked` 저장) — 다음: REST API 전환·전략 선택 UI

파일 드래그&드롭으로 문서 여러 개를 한 번에 비식별화하는 데스크톱 도구.

## 실행·테스트

```bash
cd apps/desktop
flutter run -d windows      # 실행
flutter test                # 위젯 테스트
flutter build windows       # 릴리스 빌드
```

Flutter 3.44.6 stable / Windows 기준. 새 패키지 추가 전 라이선스 확인 후 [SBOM.md](../../SBOM.md)에 기록.

## 구조

```
lib/
  main.dart                    # 앱 루트 — 테마·첫 화면 연결만
  models/
    detection.dart             # core Detection과 1:1 (API 계약 v1 스키마) + 한국어 요약
    file_task.dart             # 파일 1개의 처리 상태 (대기/처리 중/완료/실패)
  services/
    anonymizer.dart            # 비식별화 백엔드 인터페이스 (CLI ↔ REST 교체 지점)
    cli_anonymizer.dart        # core CLI 서브프로세스 호출 (stdin UTF-8)
    batch_processor.dart       # 읽기 → 비식별화 → _masked 저장 순차 배치
  screens/
    home_screen.dart           # 홈 — 작업 목록 상태 관리 + 배치 시작
  widgets/
    drop_zone.dart             # OS 파일 드래그&드롭 수신 영역 (desktop_drop)
test/
  batch_processor_test.dart    # 배치 로직 유닛 테스트 (가짜 백엔드)
  widget_test.dart             # 드롭존·목록·처리 흐름 위젯 테스트
  fakes.dart                   # 테스트용 가짜 Anonymizer
```

- Windows에서 플러그인 빌드에는 **개발자 모드**가 필요하다 (설정 → 개발자용 → 개발자 모드 켬).
- 실행하는 PC에 `maskingtape` CLI가 PATH에 있어야 처리가 동작한다 (`pip install -e packages/core` 후 venv Scripts를 PATH에 — REST API 전환 전까지의 개발용 전제).

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. pubspec 의존성 추가 시 [SBOM.md](../../SBOM.md)에 한 줄 추가 — 라이선스 확인 필수
3. 처리 자체는 `apps/api` 호출 또는 core CLI 실행으로 — **탐지 로직을 Dart로 재구현하지 않는다**
