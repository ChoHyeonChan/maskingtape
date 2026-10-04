// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'services/bundled_licenses.dart';
import 'theme.dart';

void main() {
  // 설치판에 함께 실린 구성요소(임베디드 Python 등)의 고지문을 라이선스 화면에 보탠다.
  registerBundledLicenses();
  runApp(const MaskingtapeApp());
}

/// 앱 루트 — 테마와 첫 화면 연결만 담당한다.
class MaskingtapeApp extends StatelessWidget {
  const MaskingtapeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '마스킹테이프',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
    );
  }
}
