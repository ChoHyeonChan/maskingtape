# apps/desktop — Flutter 데스크톱 앱

**담당: 김준형** · 상태: 🚧 뼈대 진행 중 (드롭존 빈 화면)

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
  main.dart               # 앱 루트 — 테마·첫 화면 연결만
  screens/
    home_screen.dart      # 홈 — 드롭존 자리 표시 (드래그&드롭 수신은 다음 단계)
test/
  widget_test.dart        # 홈 화면 스모크 테스트
```

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. pubspec 의존성 추가 시 [SBOM.md](../../SBOM.md)에 한 줄 추가 — 라이선스 확인 필수
3. 처리 자체는 `apps/api` 호출 또는 core CLI 실행으로 — **탐지 로직을 Dart로 재구현하지 않는다**
