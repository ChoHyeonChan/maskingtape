// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:io';

/// 설치판의 폴더 배치 — 앱 exe가 있는 폴더 기준.
///
/// 설치파일 빌드 스크립트(`installer/build.py`, #617)가 같은 배치로 조립한다. 여기와
/// 어긋나면 설치판이 CLI나 고지문을 찾지 못하므로 두 곳을 함께 고친다.
///
/// ```
/// <설치 폴더>\
///   maskingtape_desktop.exe
///   python\python.exe          임베디드 Python (+ Lib\site-packages\maskingtape)
///   licenses\*.txt             함께 실린 제3자 구성요소의 고지문
/// ```
const bundledPythonRelativePath = r'python\python.exe';
const bundledLicensesRelativePath = 'licenses';

/// 설치 폴더(앱 exe가 있는 폴더) 아래의 경로를 만든다.
///
/// [executable]은 테스트용 주입 — 기본은 실제 exe 위치다. exe 경로를 직접 자른다:
/// `File(exe).parent`는 Linux(CI 테스트)에서 `\`를 구분자로 보지 않아 '.'이 된다.
/// 앱은 Windows 전용이지만 테스트는 양쪽에서 돈다.
String inInstallDir(String relative, {String? executable}) {
  final exe = executable ?? Platform.resolvedExecutable;
  final cut = exe.lastIndexOf(RegExp(r'[\\/]'));
  final dir = cut < 0 ? '.' : exe.substring(0, cut);
  final sep = cut < 0 ? Platform.pathSeparator : exe[cut];
  return '$dir$sep$relative';
}
