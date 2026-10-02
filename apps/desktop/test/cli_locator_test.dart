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
    // 임베디드 Python은 PYTHONUTF8을 무시하므로 -X utf8이 꼭 있어야 한글이 안 깨진다.
    expect(cli.leadingArgs, ['-X', 'utf8', '-m', 'maskingtape.cli']);
  });

  test('동봉 Python이 없으면 PATH의 maskingtape로 돌아간다 (개발 환경)', () {
    final cli = locateCli(executable: exe, exists: (_) => false);
    expect(cli.executable, 'maskingtape');
    expect(cli.leadingArgs, isEmpty);
  });
}
