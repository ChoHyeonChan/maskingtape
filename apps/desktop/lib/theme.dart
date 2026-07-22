import 'package:flutter/material.dart';

/// 마스킹테이프 브랜드 테마 — "페리윙클" 방향 (시안 C).
///
/// 부드러운 라벤더-블루 바탕에 페리윙클 액센트, 큰 라운딩.
/// 비개발자(사무직·연구자)가 쓰는 친근한 도구라는 정체성.
/// 상태(완료/처리 중/대기/실패)는 파스텔 칩 색으로 구분한다.
abstract final class AppTheme {
  static const periwinkle = Color(0xFF6A74E8);
  static const ink = Color(0xFF2B2E3F);

  /// 라이트 모드 바탕 — 라벤더 기 도는 회백.
  static const ground = Color(0xFFF4F5FC);

  /// 패널 테두리.
  static const line = Color(0xFFE5E7F5);

  /// 드롭존 점선.
  static const dashedLine = Color(0xFFC8CDF0);

  // 상태 칩 (배경, 글자) — 라이트 기준. 다크에선 글자색만 쓰고 배경은 반투명 처리.
  static const doneBg = Color(0xFFDFF3EA);
  static const doneFg = Color(0xFF2C8A63);
  static const runBg = Color(0xFFE6E9FD);
  static const runFg = Color(0xFF5A64D8);
  static const waitBg = Color(0xFFF0F1F6);
  static const waitFg = Color(0xFF8D92AD);
  static const failBg = Color(0xFFFFE9E4);
  static const failFg = Color(0xFFC4553F);

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(seedColor: periwinkle).copyWith(
      primary: periwinkle,
      onPrimary: Colors.white,
      surface: Colors.white,
      onSurface: ink,
      outlineVariant: line,
      error: failFg,
    );
    return _base(scheme, scaffold: ground);
  }

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: periwinkle,
      brightness: Brightness.dark,
    );
    return _base(scheme);
  }

  static ThemeData _base(ColorScheme scheme, {Color? scaffold}) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scaffold,
      appBarTheme: AppBarTheme(
        backgroundColor: scaffold,
        surfaceTintColor: Colors.transparent,
        centerTitle: false,
        titleSpacing: 28,
      ),
      textTheme: const TextTheme(
        titleLarge: TextStyle(fontWeight: FontWeight.w700, letterSpacing: -0.3),
        titleMedium:
            TextStyle(fontWeight: FontWeight.w600, letterSpacing: -0.2),
        labelLarge: TextStyle(fontWeight: FontWeight.w600),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          selectedBackgroundColor: scheme.primary,
          selectedForegroundColor: scheme.onPrimary,
          side: BorderSide(color: scheme.outlineVariant, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      dividerTheme: DividerThemeData(
        color: scheme.outlineVariant.withValues(alpha: 0.6),
        space: 1,
      ),
    );
  }
}
