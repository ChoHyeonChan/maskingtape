# apps/desktop — Flutter 데스크톱 앱

**담당: [@stayalive000](https://github.com/stayalive000)** · 상태: ✅ 기능 완성 (드롭 → 일괄 비식별화 → `_masked` 저장, 전략 선택·이름 정밀 탐지·결과 미리보기) — 백엔드는 로컬 CLI 우선 + REST API 폴백

파일 드래그&드롭으로 문서 여러 개를 한 번에 비식별화하는 데스크톱 도구. **Windows 전용**이다 — macOS·Linux는 아래 [지원 플랫폼](#지원-플랫폼) 참고.

## 실행·테스트

### 1. 선행조건 — 먼저 확인한다

**⓪ 지원 플랫폼: Windows** — 러너가 `windows/` 하나뿐이라 **macOS·Linux는 현재 빌드 대상이 아니다.**
그 환경에서는 같은 비식별화 기능을 CLI(`pip install maskingtape`)나
[웹 데모](https://maskingtape-lilac.vercel.app)로 쓴다. 러너를 추가하지 않은 이유는 아래 [지원 플랫폼](#지원-플랫폼) 절 참고.

아래 두 가지를 건너뛰면 **빌드가 실패하거나, 앱은 떠도 모든 파일이 실패로 표시된다.**

**① Windows 개발자 모드 (켜야 빌드된다)**

`flutter run`이 플러그인을 빌드하며 심볼릭 링크를 만드는데, 개발자 모드가 꺼져 있으면 권한이 없어 죽는다.

> 설정 → 개인 정보 보호 및 보안 → 개발자용 → **개발자 모드 켬**

**② 처리 백엔드 (있어야 파일이 처리된다)**

앱 자체는 탐지를 하지 않는다 — core에 맡긴다. 아래 **둘 중 하나**가 준비돼 있어야 한다.
(두 블록 모두 **저장소 루트**에서 실행한다.)

```powershell
# (권장) core CLI를 PATH에 — 전 기능 사용 가능
pip install -e packages/core
$env:PATH = "<저장소>\.venv\Scripts;$env:PATH"   # venv를 썼다면
maskingtape --help                                # 이게 나오면 준비 완료
```

```powershell
# 또는 REST API 서버 — mask·label·pseudonym (이름 정밀 탐지는 CLI 전용)
pip install -e packages/core
pip install -e "apps/api[dev]"
python -m uvicorn maskingtape_api.main:app --host 127.0.0.1 --port 8000
```

둘 다 없으면 앱은 정상적으로 뜨지만 처리 시 *"비식별화 백엔드에 연결하지 못했습니다"*가
파일마다 표시된다. 자세한 동작은 아래 [백엔드 절](#비식별화-백엔드--로컬-cli-먼저-없으면-rest-api) 참고.

### 2. 실행

```bash
cd apps/desktop
flutter run -d windows      # 실행
flutter test                # 테스트
flutter build windows       # 릴리스 빌드
```

Flutter 3.44.6 stable / Windows 기준. 새 패키지 추가 전 라이선스 확인 후 [SBOM.md](../../SBOM.md)에 기록.

CI([ci.yml](../../.github/workflows/ci.yml)의 `desktop` 잡)는 ubuntu에서 `flutter analyze`·`flutter test`까지만 검증한다 —
**`flutter build windows`는 CI가 검증하지 않으므로** 릴리스 빌드는 Windows PC에서 직접 확인한다.

### 3. 막히면

| 증상 | 원인과 조치 |
|---|---|
| 빌드가 symlink·권한 오류로 죽는다 | 개발자 모드가 꺼져 있다 (선행조건 ①) |
| `flutter test`가 출력 없이 멈춘다 | **Windows 사용자명에 한글 등 비ASCII 문자**가 있으면 재현된다(실측: 7분간 무응답). 임시 폴더를 ASCII 경로로 바꾸고 다시 실행한다 — `$env:TEMP='D:\dev\tmp'; $env:TMP='D:\dev\tmp'` |
| 빌드가 `LNK1104 ... .exe 파일을 열 수 없습니다` | 앱이 이미 실행 중이라 exe가 잠겨 있다. 창을 닫거나 `Get-Process maskingtape_desktop \| Stop-Process -Force` |
| 모든 파일이 "백엔드에 연결하지 못했습니다" | 선행조건 ②가 안 돼 있다 |
| macOS·Linux에서 `flutter run`이 대상 장치를 못 찾는다 (`No supported devices`) | 이 앱은 Windows 전용이다 (선행조건 ⓪). CLI나 웹 데모를 쓴다 |

## 구조

```
lib/
  main.dart                    # 앱 루트 — 테마·첫 화면 연결만
  theme.dart                   # 브랜드 테마 — 웹 tokens.css와 같은 값 (색·타이포·모서리)
  kind_colors.dart             # 탐지 종류별 강조색 — 웹 --kind-*와 동일 (결과 미리보기용)
  models/
    detection.dart             # core Detection과 1:1 (API 계약 v1 스키마) + 한국어 요약
    file_task.dart             # 파일 1개의 처리 상태 (대기/처리 중/완료/실패)
  services/
    anonymizer.dart            # 비식별화 백엔드 인터페이스 + 예외 타입
    cli_anonymizer.dart        # core CLI 서브프로세스 호출 (stdin UTF-8)
    rest_anonymizer.dart       # apps/api REST 호출 (dart:io HttpClient, 의존성 추가 없음)
    fallback_anonymizer.dart   # 백엔드를 순서대로 시도 (조합만 담당)
    default_backend.dart       # 기본 조립 — CLI 먼저, 없으면 REST
    llm_status.dart            # 로컬 Ollama 준비 상태 확인 (상태만 조회 — 탐지는 하지 않는다)
    file_reader.dart           # 파일 검증(확장자·크기·바이너리) + UTF-8/CP949 디코딩
    file_picker.dart           # OS 파일 선택 대화상자 (file_selector)
    shell.dart                 # 탐색기에서 결과 파일 열기
    batch_processor.dart       # 읽기 → 비식별화 → _masked 저장 순차 배치 (취소 지원)
  screens/
    home_screen.dart           # 홈 — 작업 목록 상태 관리 + 배치 시작
  widgets/
    drop_zone.dart             # 드래그&드롭 수신 + 찾아보기 버튼 (desktop_drop, 점선 드롭존)
    status_pill.dart           # 파일 상태 칩
    llm_status_pill.dart       # 로컬 LLM 준비 상태 칩 (누르면 다시 확인)
    tape_strip.dart            # 시그니처 — 뜯어 붙인 마스킹테이프 한 조각 (직접 그림)
    redacted_text.dart         # 테이프로 가려진 글자 (빈 화면 예시용)
    result_preview_dialog.dart # 원문 하이라이트 vs 마스킹 결과 비교 다이얼로그
test/
  batch_processor_test.dart    # 배치 로직 유닛 테스트 (가짜 백엔드, 취소 포함)
  file_reader_test.dart        # 인코딩 폴백·검증 규칙 테스트
  rest_anonymizer_test.dart    # REST 호출 — 루프백에 실제 HTTP 서버를 띄워 검증
  fallback_anonymizer_test.dart# 백엔드 전환 규칙 테스트
  llm_status_test.dart         # Ollama 상태 확인 — 가짜 Ollama 서버로 4가지 상태 검증
  widget_test.dart             # 드롭존·목록·처리 흐름 위젯 테스트
  fakes.dart                   # 테스트용 가짜 Anonymizer
  manual_rest_smoke.dart       # 수동 확인용 — 실제로 뜬 apps/api에 붙여본다 (자동 실행 아님)
```

## 비식별화 백엔드 — 로컬 CLI 먼저, 없으면 REST API

처리는 **core CLI를 먼저** 시도하고, 이 PC에 CLI가 없으면 **`apps/api` REST**(기본 `http://127.0.0.1:8000`)로 넘어간다.

순서를 이렇게 둔 이유:

- 로컬 CLI는 기능이 온전하다 — 가명처리(`pseudonym`)는 #309 이후 API도 지원하지만, **이름 정밀 탐지(LLM)는 여전히 CLI 전용**이다(배포 API는 규칙 기반 탐지만 제공한다). 텍스트가 이 PC를 벗어나지도 않는다.
- CLI를 설치하지 않은 PC에서도 앱이 그냥 동작해야 한다 — 설치 없이 실행하는 배포판·시연 상황.

백엔드를 넘기는 건 **닿지 못했을 때뿐**이다(`AnonymizerUnavailableException` — CLI가 PATH에 없거나 API 서버가 안 떠 있음). 처리 중 발생한 오류(예: Ollama 미실행)는 백엔드를 바꿔도 같은 결과라 그대로 보여준다 — 넘기면 원인만 가려진다.

API 경로에서 지원하지 않는 옵션을 고르면 네트워크를 타기 전에 거절하고, "CLI를 설치하면 이 PC에서 처리할 수 있습니다"라고 안내한다.

## 디자인 — 웹 플레이그라운드와 같은 브랜드

색·모서리·글꼴 체계는 **웹([apps/web](../web)) `tokens.css`의 값을 그대로 옮겼다**(#442).
사용자가 눈으로 보는 표면은 웹과 데스크톱 둘뿐이라, 이 둘이 다르면 같은 제품으로
읽히지 않는다. 웹이 바뀌면 [theme.dart](lib/theme.dart)의 상수만 같이 고친다.

- **팔레트**: 브랜드 남색 `#183A8B`(로고·선택된 세그먼트·완료·테이프), 행동 파랑 `#0B55F0`
  (주 버튼 하나에만), 바탕 `#F6F8FB` + 흰 패널(테두리 남색 18%, 모서리 14). 빨강은 실패에만.
- **헤더**: 웹과 같은 로고 PNG(`assets/maskingtape-logo-blue.png` — 팀 자산, [apps/web/public](../web/public)과 동일 파일) + 한 줄 설명.
- **테이프 모티프는 유지**한다([tape_strip.dart](lib/widgets/tape_strip.dart)) — 뜯긴 가장자리와 살짝 기운 각도를
  직접 그린다. 색만 로고의 파란 테이프 롤과 같은 남색이다. 빈 화면의 예시 문서, 진행률 막대,
  완료 칩이 모두 이 색으로 이어진다. "가려진 자리 = 테이프가 붙은 자리 = 완료".
- **탐지 종류별 색**([kind_colors.dart](lib/kind_colors.dart)): 결과 미리보기의 하이라이트는 웹 `--kind-*`와 같은 색이다
  (주민번호 남색·전화 초록·이메일 자주·주소 보라…). 웹 결과 화면의 점과 같은 색이라 두 표면을
  오가도 색만 보고 종류를 알아본다. 모르는 kind는 중립 회색.
- 글꼴은 시스템 글꼴을 쓴다. 웹도 `Inter, "Segoe UI", system-ui` 폴백 체인이라 폰트 파일을
  싣지 않는다 — Windows에선 둘 다 Segoe UI + 맑은 고딕으로 렌더된다. 한글 글꼴을 번들하려면
  라이선스 확인과 SBOM 등록이 필요한데 팀 허용 목록(MIT/Apache/BSD/ISC)에 흔한 한글 글꼴
  라이선스(OFL)가 없다.

앱 아이콘(`windows/runner/resources/app_icon.ico`)은 아직 이전 팔레트(노란 테이프)다 — 파란색 교체는 별도 이슈.

입력 파일 규칙: txt·csv·tsv·md·json·log, 10MB 이하, UTF-8 또는 CP949(자동 판별).
결과 `_masked` 파일은 항상 UTF-8로 저장한다. `_masked` 파일 재드롭·바이너리·빈 파일은 건너뛴다.

## 이름 정밀 탐지 (선택)

툴바의 **이름 정밀 탐지**를 켜면 CLI에 `--llm`을 붙여 이름을 로컬 LLM으로 판단한다
(규칙판이 놓치거나 오탐하는 인명을 문맥으로 걸러낸다).

툴바의 **상태 칩**이 이 PC의 로컬 LLM 준비 상태를 미리 보여준다 — 처리에 실패한 뒤에야
"Ollama를 켰어야 했구나"를 알게 되는 걸 막기 위해서다. 누르면 다시 확인한다.

| 표시 | 뜻 | 할 일 |
|---|---|---|
| `LLM 확인 중…` | 확인 중 | — |
| `Ollama 미실행` | 연결 실패 | Ollama를 실행한다 |
| `모델 없음` | Ollama는 떠 있는데 모델이 없다 | `ollama pull qwen2.5:7b` |
| `LLM 준비됨` | 모델은 받아뒀지만 메모리에 없다 | 그대로 써도 된다 (첫 호출에서 로딩 시간) |
| `LLM 로드됨` | 메모리에 올라가 있다 | 바로 응답한다 |

상태 확인은 Ollama의 `/api/tags`·`/api/ps`를 **읽기만** 한다 — 원문 텍스트를 보내지 않고,
탐지도 하지 않는다(탐지는 core의 몫). 확인 대상 모델은 core `name_llm.py`의
`DEFAULT_MODEL`과 같은 값을 유지해야 한다.

- **꺼짐이 기본** — 끈 상태에서는 규칙 전용이라 Ollama 없이도 그대로 동작한다.
- 켜려면 이 PC에서 **Ollama가 실행 중**이고 모델(`ollama pull qwen2.5:7b`)이 있어야 한다.
- 준비가 안 됐으면 해당 파일만 실패로 표시되고 **core가 준 안내 문구가 그대로** 보인다(앱이 덮어쓰지 않는다). 나머지 파일 처리는 계속된다.
- CLI를 탐지·마스킹 두 번 호출하므로 LLM 모드에서는 파일당 모델 호출도 두 번이다 — 그만큼 느리다.

- 이름 정밀 탐지는 **CLI 경로에서만** 동작한다 — API 백엔드로 넘어간 상태에서 켜면 안내와 함께 거절된다.

> 개발자 모드·백엔드 준비는 위 [선행조건](#1-선행조건--먼저-확인한다)으로 옮겼다 — 여기 묻혀 있으면
> 위에서부터 따라 하는 사람이 못 보고 설치에 실패한다.

## 지원 플랫폼

**Windows만 지원한다.** `apps/desktop/`에 플랫폼 러너가 `windows/` 하나뿐이라 macOS·Linux에서는 빌드되지 않는다.

- macOS·Linux 사용자는 **CLI(`pip install maskingtape`)** 또는 **[웹 데모](https://maskingtape-lilac.vercel.app)**로 같은 비식별화를 할 수 있다 —
  탐지·마스킹은 전부 core에 있고 이 앱은 그걸 감싸는 껍데기다. CLI는 앱과 기능이 같고(이름 정밀 탐지 포함), 웹 데모는 규칙 기반 탐지만 제공한다.
- `flutter create --platforms=macos,linux .`로 러너를 추가할 수는 있지만, 팀에 그 환경이 없어 동작을 확인할 수 없다.
  검증 없이 추가하면 "폴더는 있는데 빌드가 깨지는" 상태가 되어 더 나쁘므로 **대회 이후 과제로 남긴다** (#404).

## 규칙

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. pubspec 의존성 추가 시 [SBOM.md](../../SBOM.md)에 한 줄 추가 — 라이선스 확인 필수
3. 처리 자체는 `apps/api` 호출 또는 core CLI 실행으로 — **탐지 로직을 Dart로 재구현하지 않는다**
