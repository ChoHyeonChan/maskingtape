// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:io';

import 'install_layout.dart';

/// 실행할 CLI — 실행 파일과, 사용자 인자 앞에 붙일 고정 인자.
class CliCommand {
  const CliCommand(this.executable, [this.leadingArgs = const []]);

  final String executable;
  final List<String> leadingArgs;
}

/// 동봉 Python으로 CLI 모듈을 부르는 인자.
///
/// - `-m maskingtape.cli`: pip이 만드는 `Scripts\maskingtape.exe` 런처를 쓰지 않는다. 런처를
///   만들려면 pip을 동봉해야 하고, 그만큼 고지할 제3자 구성요소가 늘어난다.
/// - `-B`: `.pyc`(`__pycache__`)를 쓰지 않는다. 설치 폴더에 실행 중 생기는 파일이 없어야 제거할 때
///   설치한 파일만 지우면 폴더가 깨끗이 사라진다(제거 단계에서 `python\` 폴더를 통째로 지우는 방식은
///   사용자가 설치 경로를 다른 Python 폴더와 겹치게 잡으면 남의 파일까지 지울 수 있어 쓰지 않는다).
///   캐시 없이 도는 비용은 호출당 0.03초쯤이다.
/// - `-X utf8`: core CLI가 표준입출력을 UTF-8로 고정하지만(`cli.py`의 `_read_stdin`·`_use_utf8_output`),
///   그 밖의 경로(파일 열기 기본 인코딩 등)도 UTF-8로 맞추려고 함께 준다.
const bundledCliArgs = ['-B', '-X', 'utf8', '-m', 'maskingtape.cli'];

/// 어떤 `maskingtape` CLI를 실행할지 정한다.
///
/// 1. 앱 exe 옆에 동봉된 Python([bundledPythonRelativePath])이 있으면 그것으로 CLI 모듈을
///    부른다 — 설치판 사용자는 Python도 PATH 설정도 없다.
/// 2. 없으면 PATH의 `maskingtape` — 소스에서 `flutter run`으로 돌리는 개발 환경(venv).
///
/// [executable]·[exists]는 테스트용 주입 — 기본은 실제 exe 위치와 파일 존재 여부다.
CliCommand locateCli({String? executable, bool Function(String path)? exists}) {
  final python = inInstallDir(bundledPythonRelativePath, executable: executable);
  final found = exists ?? (path) => File(path).existsSync();
  return found(python)
      ? CliCommand(python, bundledCliArgs)
      : const CliCommand('maskingtape');
}
