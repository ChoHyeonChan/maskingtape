# 데스크톱 설치파일 (Windows)

`maskingtape-desktop-<버전>-windows-x64-setup.exe`를 만드는 스크립트다([#617](https://github.com/ChoHyeonChan/maskingtape/issues/617)).
설치판을 받은 사람은 Python도 PATH 설정도 없으므로, CLI를 돌릴 Python을 함께 넣는다.

## 만드는 법

Windows에서, 저장소 루트에서 실행한다.

```powershell
# 준비물: Flutter(PATH), Python 3.10+ (pip 포함), Inno Setup 6
winget install JRSoftware.InnoSetup

python apps/desktop/installer/build.py --version 0.1.0
# 결과: apps/desktop/build/installer/dist/maskingtape-desktop-0.1.0-windows-x64-setup.exe
```

| 옵션 | 뜻 |
|---|---|
| `--version X.Y.Z` | 설치파일 버전. 생략하면 `pubspec.yaml`의 `version` |
| `--skip-flutter-build` | 이미 있는 `flutter build windows --release` 결과물을 그대로 쓴다 |
| `--no-installer` | 묶음 폴더(`build/installer/bundle/`)까지만 만든다 — Inno Setup 없이 내용을 확인할 때 |

`build.py`는 표준 라이브러리만 쓴다. 받는 파일은 전부 SHA-256을 고정해 두었고, 다르면 멈춘다.

## 설치 폴더에 들어가는 것

```
<설치 폴더>\                       기본: %LOCALAPPDATA%\Programs\maskingtape (관리자 권한 불필요)
  maskingtape_desktop.exe          Flutter 앱 (+ flutter_windows.dll, 플러그인 dll, data\)
  python\                          Python 임베디드 배포판 3.13.2 (amd64)
    python.exe
    Lib\site-packages\maskingtape\ core wheel을 푼 것 (우리 코드)
  licenses\*.txt                   함께 실린 제3자 구성요소의 고지문
  LICENSE.txt                      Apache-2.0 (우리 코드)
  THIRD_PARTY_NOTICES.md           저장소의 고지 파일 사본
  BUNDLE_MANIFEST.txt              제3자 파일별 SHA-256 — SBOM의 근거
```

이 배치는 `lib/services/install_layout.dart`와 같아야 한다. 앱은 exe 옆에 `python\python.exe`가
있으면 `python.exe -X utf8 -m maskingtape.cli`로 CLI를 부르고(`cli_locator.dart`), 없으면 PATH의
`maskingtape`를 쓴다.

- **pip은 넣지 않는다.** wheel을 site-packages에 풀기만 한다. core에 런타임 의존성이 없어서 가능한
  방법이고, 의존성이 생기면 `build.py`가 멈춘다.
- **`-X utf8`이 필요한 이유**: 임베디드 Python은 `._pth` 파일 때문에 격리 모드로 떠서 `PYTHONUTF8`
  환경변수를 무시한다. 플래그가 없으면 한글이 cp949로 깨진다.
- **Ollama와 모델은 넣지 않는다**(4.7GB). 설치 마지막 화면에 Ollama 설치 페이지를 여는 선택 항목이 있다.
  없어도 규칙 탐지는 그대로 동작한다.

## 제3자 고지 (§2-8)

설치판은 실행 화면에서 고지문을 보여 줘야 한다. 앱의 ⓘ 버튼이 여는 라이선스 화면에 두 가지가 합쳐진다.

1. Flutter 엔진·Dart 패키지 — Flutter 빌드가 모은 목록(자동).
2. 설치파일에 따로 넣는 것 — `licenses\*.txt`를 앱이 읽어 보탠다(`bundled_licenses.dart`). 파일 이름이 항목 이름이다.

| `licenses\` 파일 | 출처 |
|---|---|
| `Python 3.13.2 (CPython).txt` | 임베디드 zip 안의 `LICENSE.txt` (PSF 계약, bzip2·libffi, Microsoft Distributable Code 조건 포함) |
| `Python 3.13.2 - incorporated software.txt` | CPython `Doc/license.rst` — expat·libmpdec 등 `.pyd`에 정적으로 들어간 것들 |
| `OpenSSL 3.0.15.txt` | OpenSSL 저장소의 `LICENSE.txt`(Apache-2.0) — 임베디드 zip의 `LICENSE.txt`에는 없다 |
| `SQLite 3.45.3.txt` | 퍼블릭 도메인 고지 |
| `Microsoft Visual C++ Runtime.txt` | `vcruntime140*.dll` — 조건은 Python 라이선스의 해당 절을 가리킨다 |
| `Inno Setup (installer).txt` | 빌드에 쓴 Inno Setup의 `license.txt` — setup.exe 안에 설치 실행부가 들어간다 |

**동봉물을 바꾸면**(Python 버전 등) `build.py` 위쪽의 버전·주소·해시 상수를 고치고, 팀장에게 알려
`SBOM.md`·`THIRD_PARTY_NOTICES.md`를 함께 고친다. `BUNDLE_MANIFEST.txt`가 옮겨 적을 근거다.

## 알아 둘 점

- **코드 서명이 없다.** 처음 실행하면 Windows SmartScreen이 막는다 — "추가 정보 → 실행"을 누른다.
- **Visual C++ 런타임은 넣지 않는다.** Flutter 앱은 `msvcp140.dll` 등이 있어야 뜬다. 대부분의 PC에는
  이미 있고, 없으면 설치 프로그램이 내려받을 주소를 알려 준다.
- **자동 업데이트가 없다.** 새 버전은 GitHub Releases에서 받아 다시 설치한다(같은 자리에 덮어 깔린다).
- 지원 대상은 Windows 10/11 x64다.
