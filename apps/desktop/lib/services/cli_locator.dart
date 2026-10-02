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
/// - `-X utf8`: 임베디드 Python은 `._pth` 파일 때문에 격리 모드로 떠서 `PYTHONUTF8`
///   환경변수를 무시한다. 플래그로 줘야 파이프가 UTF-8이 된다(아니면 한글이 cp949로 깨진다).
const bundledCliArgs = ['-X', 'utf8', '-m', 'maskingtape.cli'];

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
