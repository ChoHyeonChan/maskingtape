// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'install_layout.dart';

/// 설치판에 함께 실린 제3자 구성요소의 고지문을 라이선스 화면(ⓘ)에 등록한다 (§2-8, #617).
///
/// Flutter 엔진·Dart 패키지의 라이선스는 빌드가 모아 주지만, 설치파일에 따로 넣는 것들
/// (임베디드 Python과 그 안의 OpenSSL·SQLite 등, 설치 프로그램 Inno Setup)은 Flutter가
/// 모른다. 빌드 스크립트가 exe 옆 `licenses\` 폴더에 `이름.txt`로 넣어 두면 여기서 읽어
/// 같은 화면에 보탠다 — 파일 이름(확장자 제외)이 목록의 항목 이름이 된다.
///
/// 폴더가 없으면(소스에서 `flutter run`하는 개발 환경 — 동봉물이 없다) 아무것도 하지 않는다.
void registerBundledLicenses({String? executable}) {
  final dir = Directory(
    inInstallDir(bundledLicensesRelativePath, executable: executable),
  );
  if (!dir.existsSync()) return;

  LicenseRegistry.addLicense(() async* {
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.toLowerCase().endsWith('.txt'))
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));
    for (final file in files) {
      final name = file.uri.pathSegments.last;
      yield LicenseEntryWithLineBreaks(
        [name.substring(0, name.length - '.txt'.length)],
        // 고지문은 남이 쓴 파일이라 인코딩을 장담할 수 없다 — 깨진 바이트가 있어도 화면은 뜨게 한다.
        utf8.decode(await file.readAsBytes(), allowMalformed: true),
      );
    }
  });
}
