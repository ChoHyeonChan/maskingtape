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
  theme.dart                   # 페리윙클 브랜드 테마 (색·라운딩·컴포넌트 스타일)
  models/
    detection.dart             # core Detection과 1:1 (API 계약 v1 스키마) + 한국어 요약
    file_task.dart             # 파일 1개의 처리 상태 (대기/처리 중/완료/실패)
  services/
    anonymizer.dart            # 비식별화 백엔드 인터페이스 (CLI ↔ REST 교체 지점)
    cli_anonymizer.dart        # core CLI 서브프로세스 호출 (stdin UTF-8)
    file_reader.dart           # 파일 검증(확장자·크기·바이너리) + UTF-8/CP949 디코딩
    file_picker.dart           # OS 파일 선택 대화상자 (file_selector)
    shell.dart                 # 탐색기에서 결과 파일 열기
    batch_processor.dart       # 읽기 → 비식별화 → _masked 저장 순차 배치 (취소 지원)
  screens/
    home_screen.dart           # 홈 — 작업 목록 상태 관리 + 배치 시작
  widgets/
    drop_zone.dart             # 드래그&드롭 수신 + 찾아보기 버튼 (desktop_drop, 점선 드롭존)
    status_pill.dart           # 파일 상태 파스텔 칩
    result_preview_dialog.dart # 원문 하이라이트 vs 마스킹 결과 비교 다이얼로그
test/
  batch_processor_test.dart    # 배치 로직 유닛 테스트 (가짜 백엔드, 취소 포함)
  file_reader_test.dart        # 인코딩 폴백·검증 규칙 테스트
  widget_test.dart             # 드롭존·목록·처리 흐름 위젯 테스트
  fakes.dart                   # 테스트용 가짜 Anonymizer
```

입력 파일 규칙: txt·csv·tsv·md·json·log, 10MB 이하, UTF-8 또는 CP949(자동 판별).
결과 `_masked` 파일은 항상 UTF-8로 저장한다. `_masked` 파일 재드롭·바이너리·빈 파일은 건너뛴다.

## 이름 정밀 탐지 (선택)

툴바의 **이름 정밀 탐지**를 켜면 CLI에 `--llm`을 붙여 이름을 로컬 LLM으로 판단한다
(규칙판이 놓치거나 오탐하는 인명을 문맥으로 걸러낸다).

- **꺼짐이 기본** — 끈 상태에서는 규칙 전용이라 Ollama 없이도 그대로 동작한다.
- 켜려면 이 PC에서 **Ollama가 실행 중**이고 모델(`ollama pull qwen2.5:7b`)이 있어야 한다.
- 준비가 안 됐으면 해당 파일만 실패로 표시되고 **core가 준 안내 문구가 그대로** 보인다(앱이 덮어쓰지 않는다). 나머지 파일 처리는 계속된다.
- CLI를 탐지·마스킹 두 번 호출하므로 LLM 모드에서는 파일당 모델 호출도 두 번이다 — 그만큼 느리다.

- Windows에서 플러그인 빌드에는 **개발자 모드**가 필요하다 (설정 → 개발자용 → 개발자 모드 켬).
- 실행하는 PC에 `maskingtape` CLI가 PATH에 있어야 처리가 동작한다 (`pip install -e packages/core` 후 venv Scripts를 PATH에 — REST API 전환 전까지의 개발용 전제).

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. pubspec 의존성 추가 시 [SBOM.md](../../SBOM.md)에 한 줄 추가 — 라이선스 확인 필수
3. 처리 자체는 `apps/api` 호출 또는 core CLI 실행으로 — **탐지 로직을 Dart로 재구현하지 않는다**
