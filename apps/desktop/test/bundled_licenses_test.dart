// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/bundled_licenses.dart';

/// 설치판 고지문 등록(#617) — exe 옆 `licenses\*.txt`가 라이선스 화면의 항목이 된다.
void main() {
  late Directory install;
  late String exe;

  setUp(() {
    install = Directory.systemTemp.createTempSync('maskingtape_install_');
    exe = '${install.path}${Platform.pathSeparator}maskingtape_desktop.exe';
  });

  tearDown(() {
    LicenseRegistry.reset();
    install.deleteSync(recursive: true);
  });

  Future<Map<String, String>> registered() async {
    final entries = await LicenseRegistry.licenses.toList();
    return {
      for (final e in entries)
        e.packages.single: e.paragraphs.map((p) => p.text).join('\n'),
    };
  }

  test('licenses 폴더의 txt가 파일 이름을 항목 이름으로 해서 등록된다', () async {
    final dir = Directory('${install.path}${Platform.pathSeparator}licenses')
      ..createSync();
    File('${dir.path}${Platform.pathSeparator}Python 3.13.2 (CPython).txt')
        .writeAsStringSync('PSF LICENSE AGREEMENT\n\n합성 고지문 첫 문단.');
    File('${dir.path}${Platform.pathSeparator}OpenSSL 3.0.15.txt')
        .writeAsStringSync('Apache License 2.0');
    // txt가 아닌 파일은 고지문이 아니다.
    File('${dir.path}${Platform.pathSeparator}readme.md')
        .writeAsStringSync('무시');

    registerBundledLicenses(executable: exe);

    final licenses = await registered();
    expect(licenses.keys, ['OpenSSL 3.0.15', 'Python 3.13.2 (CPython)']);
    expect(licenses['Python 3.13.2 (CPython)'], contains('합성 고지문 첫 문단.'));
  });

  test('licenses 폴더가 없으면(개발 환경) 아무것도 등록하지 않는다', () async {
    registerBundledLicenses(executable: exe);

    expect(await registered(), isEmpty);
  });
}
