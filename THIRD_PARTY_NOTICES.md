# 서드파티 고지 (Third-Party Notices)

maskingtape 배포물에 **코드가 함께 실려 나가는** 제3자 소프트웨어와, 저장소 소스에 들어 있는
제3자 템플릿 파일의 출처와 라이선스를 고지한다.
의존성 전체 목록은 [SBOM.md](SBOM.md)에 있다.

## 고지 대상

제3자 코드가 함께 실리는 배포물은 둘이다. **웹 데모의 빌드 결과물**(`apps/web/dist/`)과
**데스크톱 앱 Windows 설치파일**(GitHub Releases의 `setup.exe`)이다.

### 웹 데모 빌드 결과물

이 파일들은 방문자의 브라우저로 전송되므로 아래 소프트웨어를 고지한다.
웹 데모 화면에서 이 파일로 가는 링크는 [#439](https://github.com/ChoHyeonChan/maskingtape/issues/439)에서 추가한다.

| 소프트웨어 | 버전 | 라이선스 | 저작권 | 원본 | 빌드 결과물 안의 위치 |
|---|---|---|---|---|---|
| pdf.js (`pdfjs-dist`) | 6.2.108 | Apache-2.0 | Copyright 2024 Mozilla Foundation | https://github.com/mozilla/pdf.js | `assets/pdf-*.js`, `assets/pdf.worker.min-*.mjs` |
| React (`react`) | 19.2.7 | MIT | Copyright (c) Meta Platforms, Inc. and affiliates. | https://github.com/facebook/react | `assets/index-*.js` |
| React DOM (`react-dom`) | 19.2.7 | MIT | Copyright (c) Meta Platforms, Inc. and affiliates. | https://github.com/facebook/react | `assets/index-*.js` |
| Scheduler (`scheduler`) | 0.27.0 | MIT | Copyright (c) Meta Platforms, Inc. and affiliates. | https://github.com/facebook/react | `assets/index-*.js` |

네 가지 모두 소스를 고치지 않았다. 빌드 도구(Vite)가 압축해서 결과물에 넣는다.
pdfjs-dist 6.2.108 패키지에는 NOTICE 파일이 없다.
React 계열은 빌드 과정에서 파일 안의 라이선스 주석이 빠지므로 이 파일로 고지를 대신한다.

### 데스크톱 앱 Windows 설치파일 (`setup.exe`)

Python이 없는 PC에서도 데스크톱 앱을 쓰도록 만든 설치파일이다(GitHub Releases `desktop-v*`, 만드는 코드는
`apps/desktop/installer/build.py`, #617). 아래 구성요소를 함께 싣는다. `build.py`가 각 고지문을 고정한 주소에서
받아 SHA-256을 확인한 뒤 설치 폴더의 `licenses\`에 넣고, 앱의 ⓘ(「오픈소스 고지·라이선스」) 화면이 그 고지문을
보여 준다. 파일별 SHA-256은 설치 폴더의 `BUNDLE_MANIFEST.txt`에 있다.

| 소프트웨어 | 버전 | 라이선스 | 원본 | 설치 폴더 안의 위치 |
|---|---|---|---|---|
| CPython 임베디드 배포판 | 3.13.2 | PSF-2.0 | https://github.com/python/cpython | `python\` |
| OpenSSL | 3.0.15 | Apache-2.0 | https://github.com/openssl/openssl | `python\libssl-3.dll`, `python\libcrypto-3.dll` (CPython 임베디드에 들어 있음) |
| SQLite | 3.45.3 | 퍼블릭 도메인 | https://www.sqlite.org/ | `python\sqlite3.dll` (CPython 임베디드에 들어 있음) |
| Microsoft Visual C++ 런타임 | 14.42.34226.3 (`vcruntime140.dll` 기준) | Microsoft Distributable Code (오픈소스 아님) | CPython 임베디드 배포판에 포함 | `python\vcruntime140.dll`, `python\vcruntime140_1.dll` |
| pypdf | 6.19.0 | BSD-3-Clause | https://github.com/py-pdf/pypdf | `python\Lib\site-packages\pypdf\` |
| Flutter 엔진 (Windows) | 빌드에 쓴 Flutter SDK 판 | BSD-3-Clause | https://github.com/flutter/flutter | `flutter_windows.dll`, `data\icudtl.dat` |
| desktop_drop (Windows 플러그인) | 0.7.1 | Apache-2.0 | https://github.com/MixinNetwork/flutter-plugins/tree/main/packages/desktop_drop | `desktop_drop_plugin.dll` |
| file_selector_windows | 0.9.3+5 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_windows | `file_selector_windows_plugin.dll` |
| Inno Setup (설치 실행부) | 6.7.0 (desktop-v0.2.3 기준) | Inno Setup License (오픈소스 아님) | https://github.com/jrsoftware/issrc | `setup.exe` 안. 설치 뒤에는 제거 프로그램 `unins000.exe`로 남음 |

- CPython 임베디드 배포판은 `python313._pth`에 `Lib\site-packages` 한 줄을 더해(동봉한 패키지를 찾게 하는 경로 설정) 싣고, 그 밖의 파일은 바꾸지 않는다.
- CPython 임베디드 배포판에 들어 있는 나머지 구성요소(bzip2·libffi·expat·libmpdec·zlib 등)의 고지는 Python 문서
  「Licenses and Acknowledgements for Incorporated Software」 원문으로 함께 싣는다(`licenses\Python 3.13.2 - incorporated software.txt`).
- Dart 패키지(SBOM.md 부록 A-4의 런타임 의존성)는 앱 코드(`data\app.so`)에 컴파일돼 들어간다. 이 패키지들과 Flutter 엔진 안의
  제3자 구성요소(ICU·Skia 등)의 고지는 Flutter가 앱에 넣는 `data\flutter_assets\NOTICES.Z`에 있고, 같은 ⓘ 화면이 보여 준다.
- 우리 코드(core 패키지, 데스크톱 앱)는 Apache-2.0이고, 설치 폴더에 `LICENSE.txt`와 이 파일을 함께 넣는다.
- 오픈소스가 아닌 두 구성요소(Visual C++ 런타임, Inno Setup 설치 실행부)와 허용 목록 밖 라이선스를 싣는 판단 근거는
  [SBOM.md](SBOM.md) 부록 B에 있다.

## 저장소 소스에 들어 있는 제3자 템플릿

프로젝트를 처음 만들 때 각 도구가 생성한 파일 일부가 저장소에 그대로 들어 있다. 우리가 작성한
코드가 아니므로 저작권·라이선스 헤더 검사(`scripts/check_license_headers.py`)에서 빼고, 출처를 여기에 적는다.

| 템플릿 | 라이선스 | 저작권 | 원본 | 저장소 안의 위치 |
|---|---|---|---|---|
| Flutter 앱 템플릿 (Windows 실행 틀) | BSD-3-Clause | Copyright 2014 The Flutter Authors. All rights reserved. | https://github.com/flutter/flutter/tree/master/packages/flutter_tools/templates/app/windows.tmpl | `apps/desktop/windows/` |
| create-vite `react-ts` 템플릿 | MIT | Copyright (c) 2019-present, VoidZero Inc. and Vite contributors | https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts | `apps/web/tsconfig.json` |

2026-09-24에 두 공식 저장소의 원본과 파일을 대조한 결과다.

- `apps/desktop/windows/`의 18개 파일은 `flutter create`로 만들었다. 변수가 없는 템플릿 파일 11개(`runner/`의 C++·CMake·manifest,
  `flutter/CMakeLists.txt`, `.gitignore`)는 원본과 같다. 변수가 있는 템플릿 3개(`runner/main.cpp`, `runner/Runner.rc`,
  `CMakeLists.txt`)는 템플릿 변수(프로젝트 이름·조직·연도)가 채워진 것과, 생성 당시와 지금 원본의 Flutter 버전 차이
  (`CMakeLists.txt`의 컴파일 옵션 따옴표 한 곳)만 다르다. 팀이 바꾼 것은 `main.cpp`의 창 제목(한글) 한 줄과
  `Runner.rc`의 저작권·회사 표기 두 줄이다.
- `apps/desktop/windows/flutter/generated_plugin*` 3개는 Flutter 도구가 플러그인 목록으로 생성하는 파일이다.
- 앱 아이콘(`apps/desktop/windows/runner/resources/app_icon.ico`)은 템플릿 기본 아이콘을 팀이 새로 만든 것으로 바꿨다(2026-08-14).
- `apps/desktop/windows/runner/Runner.rc`의 `LegalCopyright`·`CompanyName`은 템플릿 기본값(조직 식별자 명의의 저작권 문구)을
  팀 명의("The maskingtape Authors")로 고쳤다([#454](https://github.com/ChoHyeonChan/maskingtape/issues/454)). 빌드한 exe의 속성 창에 이 문구가 보인다.
- `apps/web/tsconfig.json`은 create-vite `react-ts` 템플릿과 같다. 나머지 웹 설정 파일은 템플릿과 다르다.

## 라이선스 전문

### Apache License 2.0 (pdf.js)

전문은 이 저장소의 [LICENSE](LICENSE)와 같다. 원문은 https://www.apache.org/licenses/LICENSE-2.0 에 있다.

### MIT License (React, React DOM, Scheduler)

세 패키지는 같은 저작권 문구와 라이선스 전문을 쓴다.

```
MIT License

Copyright (c) Meta Platforms, Inc. and affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### BSD 3-Clause License (Flutter 템플릿)

Flutter 저장소(https://github.com/flutter/flutter)의 LICENSE 원문이다.

```
Copyright 2014 The Flutter Authors. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.
    * Neither the name of Google Inc. nor the names of its
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### MIT License (create-vite 템플릿)

create-vite 패키지(https://github.com/vitejs/vite/tree/main/packages/create-vite)의 LICENSE 원문이다.

```
MIT License

Copyright (c) 2019-present, VoidZero Inc. and Vite contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 고지 대상이 아닌 것

| 대상 | 이유 |
|---|---|
| PyPI 코어 패키지(`maskingtape`) | 런타임 외부 의존성이 0개라 제3자 코드가 들어가지 않는다 |
| MCP 서버, 데스크톱 앱 소스 | 소스로 배포한다. 데스크톱 앱 Windows 설치파일은 위 「고지 대상」에 적었다. 의존성은 사용자가 설치·빌드할 때 각 패키지 저장소에서 받는다. 단, 저장소에 들어 있는 Flutter 템플릿은 위 「저장소 소스에 들어 있는 제3자 템플릿」에 적었다 |
| REST API 공개 데모 | 서버에서만 실행되고 코드가 방문자에게 전달되지 않는다 |
| AI 모델(기본 maskingtape-name-1.5b, 선택 Qwen2.5-7B-Instruct) | 재배포하지 않는다. 사용자가 Ollama로 허깅페이스·Ollama 라이브러리에서 직접 받는다 |
| 학습 도구(`training/`의 torch·transformers·peft 등) | 모델을 학습할 때만 쓰고 배포물과 가중치 파일에 들어가지 않는다 |

각 의존성의 버전과 라이선스는 [SBOM.md](SBOM.md)에 있다.

## 이 파일을 고쳐야 할 때

- 제3자 코드·폰트·아이콘·이미지가 배포물(웹 빌드 결과물, 설치 파일 등)에 새로 들어갈 때
- 위 소프트웨어의 버전이 바뀔 때. 데스크톱 설치파일은 `apps/desktop/installer/build.py` 위쪽의 동봉물 상수나 빌드에 쓰는 Inno Setup 판이 바뀔 때다
- 프로젝트 생성 도구(`flutter create`, `create-vite` 등)가 만든 파일을 저장소에 새로 넣거나, 새 플랫폼(macOS·Linux 등)을 추가할 때
- 설치 파일·실행 파일(바이너리)로 배포할 때. 이때는 설치 후 실행 화면에서도 고지문을 볼 수 있어야 한다
  (2026년 9월 OpenUP 오픈소스 라이선스 컨설팅). 데스크톱 앱은 Flutter의 `showLicensePage`로 보여 줄 수 있다.
