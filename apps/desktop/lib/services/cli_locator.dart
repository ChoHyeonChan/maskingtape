// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:io';

/// 설치판이 CLI를 넣어 두는 자리 — 앱 exe가 있는 폴더 기준 상대 경로.
/// 설치파일 빌드 스크립트(#617)가 이 경로에 Python 임베디드 + `maskingtape`를 조립한다.
/// 여기와 빌드 스크립트가 어긋나면 설치판이 "CLI를 찾을 수 없습니다"로 떨어진다.
const bundledCliRelativePath = r'python\Scripts\maskingtape.exe';

/// 어떤 `maskingtape` 명령을 실행할지 정한다.
///
/// 1. 앱 exe 옆에 동봉된 CLI([bundledCliRelativePath])가 있으면 그것 — 설치판 사용자는
///    Python도 PATH 설정도 없다.
/// 2. 없으면 PATH의 `maskingtape` — 소스에서 `flutter run`으로 돌리는 개발 환경(venv).
///
/// [executable]·[exists]는 테스트용 주입 — 기본은 실제 exe 위치와 파일 존재 여부다.
String locateCli({String? executable, bool Function(String path)? exists}) {
  final exe = executable ?? Platform.resolvedExecutable;
  // exe 경로를 직접 자른다 — `File(exe).parent`는 Linux(CI 테스트)에서 `\`를 구분자로
  // 보지 않아 '.'이 된다. 앱은 Windows 전용이지만 테스트는 양쪽에서 돈다.
  final cut = exe.lastIndexOf(RegExp(r'[\/]'));
  final dir = cut < 0 ? '.' : exe.substring(0, cut);
  final sep = cut < 0 ? Platform.pathSeparator : exe[cut];
  final bundled = '$dir$sep$bundledCliRelativePath';
  final found = exists ?? (path) => File(path).existsSync();
  return found(bundled) ? bundled : 'maskingtape';
}
