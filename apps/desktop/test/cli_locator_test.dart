// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/cli_locator.dart';

void main() {
  const exe = r'C:\Program Files\maskingtape\maskingtape_desktop.exe';

  test('exe 옆에 동봉 Python이 있으면 그것으로 CLI 모듈을 부른다 (설치판)', () {
    final asked = <String>[];
    final cli = locateCli(
      executable: exe,
      exists: (path) {
        asked.add(path);
        return true;
      },
    );
    expect(cli.executable, r'C:\Program Files\maskingtape\python\python.exe');
    expect(asked, [cli.executable]);
    // -B: 설치 폴더에 __pycache__를 남기지 않는다(제거 시 폴더가 깨끗이 사라지게).
    // -X utf8: core CLI가 표준입출력을 UTF-8로 고정하지만 그 밖의 경로도 맞추려고 함께 준다.
    expect(cli.leadingArgs, ['-B', '-X', 'utf8', '-m', 'maskingtape.cli']);
  });

  test('동봉 Python이 없으면 PATH의 maskingtape로 돌아간다 (개발 환경)', () {
    final cli = locateCli(executable: exe, exists: (_) => false);
    expect(cli.executable, 'maskingtape');
    expect(cli.leadingArgs, isEmpty);
  });
}
