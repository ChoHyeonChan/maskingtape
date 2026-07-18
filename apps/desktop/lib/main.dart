import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() {
  runApp(const MaskingtapeApp());
}

/// 앱 루트 — 테마와 첫 화면 연결만 담당한다.
class MaskingtapeApp extends StatelessWidget {
  const MaskingtapeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '마스킹테이프',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF5B6B9E),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
