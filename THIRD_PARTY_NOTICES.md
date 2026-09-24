# 서드파티 고지 (Third-Party Notices)

maskingtape 배포물에 **코드가 함께 실려 나가는** 제3자 소프트웨어와, 저장소 소스에 들어 있는
제3자 템플릿 파일의 출처와 라이선스를 고지한다.
의존성 전체 목록은 [SBOM.md](SBOM.md)에 있다.

## 고지 대상

현재 제3자 코드가 들어가는 배포물은 **웹 데모의 빌드 결과물**(`apps/web/dist/`) 하나다.
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
  (`CMakeLists.txt`의 컴파일 옵션 따옴표 한 곳)만 다르다. 팀이 바꾼 것은 `main.cpp`의 창 제목(한글) 한 줄이다.
- `apps/desktop/windows/flutter/generated_plugin*` 3개는 Flutter 도구가 플러그인 목록으로 생성하는 파일이다.
- 앱 아이콘(`apps/desktop/windows/runner/resources/app_icon.ico`)은 템플릿 기본 아이콘을 팀이 새로 만든 것으로 바꿨다(2026-08-14).
- `apps/desktop/windows/runner/Runner.rc`의 `LegalCopyright` 문구("All rights reserved")는 템플릿 기본값이 남은 것이다.
  팀 명의로 고친다([#454](https://github.com/ChoHyeonChan/maskingtape/issues/454)).
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
| MCP 서버, 데스크톱 앱 | 소스로 배포한다. 의존성은 사용자가 설치·빌드할 때 각 패키지 저장소에서 받는다. 단, 저장소에 들어 있는 Flutter 템플릿은 위 「저장소 소스에 들어 있는 제3자 템플릿」에 적었다 |
| REST API 공개 데모 | 서버에서만 실행되고 코드가 방문자에게 전달되지 않는다 |
| Qwen2.5-7B-Instruct 모델 | 재배포하지 않는다. 사용자가 Ollama로 직접 받는다 |

각 의존성의 버전과 라이선스는 [SBOM.md](SBOM.md)에 있다.

## 이 파일을 고쳐야 할 때

- 제3자 코드·폰트·아이콘·이미지가 배포물(웹 빌드 결과물, 설치 파일 등)에 새로 들어갈 때
- 위 소프트웨어의 버전이 바뀔 때
- 프로젝트 생성 도구(`flutter create`, `create-vite` 등)가 만든 파일을 저장소에 새로 넣거나, 새 플랫폼(macOS·Linux 등)을 추가할 때
- 설치 파일·실행 파일(바이너리)로 배포할 때. 이때는 설치 후 실행 화면에서도 고지문을 볼 수 있어야 한다
  (2026년 9월 OpenUP 오픈소스 라이선스 컨설팅). 데스크톱 앱은 Flutter의 `showLicensePage`로 보여 줄 수 있다.
