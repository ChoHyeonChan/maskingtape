// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/cli_locator.dart';

void main() {
  const exe = r'C:\Program Files\maskingtape\maskingtape_desktop.exe';

  test('exe 옆에 동봉 CLI가 있으면 그 전체 경로를 쓴다 (설치판)', () {
    final asked = <String>[];
    final cli = locateCli(
      executable: exe,
      exists: (path) {
        asked.add(path);
        return true;
      },
    );
    expect(cli, r'C:\Program Files\maskingtape\python\Scripts\maskingtape.exe');
    expect(asked, [cli]);
  });

  test('동봉 CLI가 없으면 PATH의 maskingtape로 돌아간다 (개발 환경)', () {
    expect(locateCli(executable: exe, exists: (_) => false), 'maskingtape');
  });
}
