import 'package:flutter/material.dart';

/// 마스킹테이프 브랜드 테마 — "책상 위의 테이프" 방향.
///
/// 설계 근거(왜 이렇게 골랐는지 — 리뷰 시 이 문단부터 보면 된다):
///
/// 이 앱의 이름은 **마스킹테이프**다. 그런데 이전 테마(시안 C, 페리윙클)는 그 소재와
/// 아무 관계가 없는 라벤더-블루였다. 어느 SaaS에나 붙일 수 있는 색이라, 화면만 보고는
/// 무슨 도구인지 알 수 없었다. 그래서 팔레트를 **실제 마스킹테이프**에서 다시 가져왔다.
///
/// 핵심은 **차가운 바탕 + 따뜻한 테이프**의 대비다:
/// - 바탕([desk])과 문서([paper])는 차가운 회색 계열 — 사무실 책상과 종이.
/// - 유일하게 따뜻한 색은 [tape] 하나뿐이다. 이 색은 **가려진 자리에만** 쓴다.
///
/// 이 반전이 의도적인 선택이다. "따뜻한 크림색 바탕 + 세리프 + 테라코타"는 요즘
/// 어디서나 보이는 조합이라, 소재가 따뜻한 색이라고 바탕까지 따뜻하게 가면 그 흔한
/// 화면이 된다. 바탕을 차갑게 두면 테이프 한 조각이 화면에서 유일하게 튀어,
/// 그 자체가 이 앱의 정체성이 된다.
///
/// 상태 색도 여기서 나온다 — **완료 = 테이프가 붙은 상태**라 완료 칩만 테이프 색을 쓴다.
/// 나머지는 조용한 회색이고, 빨강은 실패에만 남긴다. 색이 셋(회색·테이프·빨강)뿐이라
/// 화면이 시끄러워지지 않는다.
///
/// 라운딩을 줄인 것도 소재에서 나왔다(이전엔 16). 테이프와 종이는 모서리가 각지고,
/// 둥근 모서리가 크면 다시 일반적인 앱처럼 보인다. 곡선은 칩에만 남긴다.
///
/// 글꼴은 시스템 글꼴을 그대로 쓴다. 한글 표시용 글꼴을 번들하려면 라이선스 확인과
/// SBOM 등록이 필요한데(§2-2), 팀 허용 목록(MIT/Apache/BSD/ISC)에 흔한 한글 글꼴
/// 라이선스(OFL)가 없어 동결 직전에 벌일 일이 아니다. 대신 **굵기·자간·크기 대비**로
/// 성격을 만든다.
abstract final class AppTheme {
  // ─── 소재 ───────────────────────────────────────────────
  /// 마스킹테이프 — 화면에서 유일하게 따뜻한 색. 가려진 자리에만 쓴다.
  static const tape = Color(0xFFE9B44C);

  /// 테이프의 그늘진 면 — 테두리·글자용(밝은 테이프 위 대비 확보).
  static const tapeDeep = Color(0xFF9A6B12);

  /// 테이프를 옅게 깐 면 — 칩 배경처럼 넓은 면적에 쓴다.
  static const tapeSoft = Color(0xFFFBEFD3);

  // ─── 바탕 ───────────────────────────────────────────────
  /// 작업대 — 창 바탕. **차가운** 회색이어야 테이프가 산다.
  static const desk = Color(0xFFEBEDF2);

  /// 종이 — 패널·카드 면.
  static const paper = Color(0xFFFFFFFF);

  /// 잉크 — 본문 글자.
  static const graphite = Color(0xFF22242C);

  /// 흐린 글자 — 보조 설명.
  static const slate = Color(0xFF6C7285);

  /// 괘선 — 패널 테두리.
  static const rule = Color(0xFFD9DDE6);

  /// 드롭존 점선.
  static const dashedLine = Color(0xFFC2C8D6);

  // ─── 다크 ───────────────────────────────────────────────
  static const deskDark = Color(0xFF14161B);
  static const paperDark = Color(0xFF1E212A);
  static const ruleDark = Color(0xFF2E3340);

  // ─── 상태 ───────────────────────────────────────────────
  // 완료만 테이프 색이다 — "테이프가 붙었다"가 곧 완료라서.
  static const doneBg = tapeSoft;
  static const doneFg = tapeDeep;
  static const runBg = Color(0xFFE4E7EF);
  static const runFg = Color(0xFF3F4557);
  static const waitBg = Color(0xFFF0F1F5);
  static const waitFg = slate;
  static const failBg = Color(0xFFFBE4DE);
  static const failFg = Color(0xFFB2432C);

  /// 모서리 — 종이·테이프는 각지다. 곡선은 칩에만.
  static const panelRadius = 10.0;
  static const controlRadius = 8.0;

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(seedColor: tape).copyWith(
      primary: graphite,
      onPrimary: Colors.white,
      secondary: tape,
      onSecondary: graphite,
      surface: paper,
      onSurface: graphite,
      onSurfaceVariant: slate,
      outlineVariant: rule,
      error: failFg,
    );
    return _base(scheme, scaffold: desk);
  }

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: tape,
      brightness: Brightness.dark,
    ).copyWith(
      primary: const Color(0xFFE8EAF0),
      onPrimary: graphite,
      secondary: tape,
      onSecondary: graphite,
      surface: paperDark,
      onSurface: const Color(0xFFE8EAF0),
      onSurfaceVariant: const Color(0xFF9AA1B4),
      outlineVariant: ruleDark,
    );
    return _base(scheme, scaffold: deskDark);
  }

  static ThemeData _base(ColorScheme scheme, {required Color scaffold}) {
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
      // 굵기와 자간으로 성격을 만든다 — 글꼴을 추가하지 않는 대신.
      textTheme: const TextTheme(
        displaySmall: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w800,
          letterSpacing: -1.1,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        titleMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
        ),
        titleSmall: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
        bodyMedium: TextStyle(fontSize: 14, height: 1.5),
        bodySmall: TextStyle(fontSize: 12.5, height: 1.45),
        // 작은 라벨은 자간을 벌려 "설명"이 아니라 "표지"로 읽히게 한다.
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.8,
        ),
        labelLarge: TextStyle(fontWeight: FontWeight.w600),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius),
          ),
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          selectedBackgroundColor: scheme.primary,
          selectedForegroundColor: scheme.onPrimary,
          side: BorderSide(color: scheme.outlineVariant),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius),
          ),
        ),
      ),
      // 진행률은 테이프가 깔리는 것으로 읽히게 — 색을 테이프로 고정한다.
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: tape,
        linearTrackColor: scheme.outlineVariant,
        linearMinHeight: 6,
      ),
      chipTheme: ChipThemeData(
        shape: const StadiumBorder(),
        side: BorderSide(color: scheme.outlineVariant),
        backgroundColor: scheme.surface,
        selectedColor: tapeSoft,
        checkmarkColor: tapeDeep,
        // 지정하지 않으면 선택 안 된 칩의 글자가 흐려져 비활성처럼 보인다.
        labelStyle: TextStyle(
          color: scheme.onSurface,
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
        iconTheme: IconThemeData(color: scheme.onSurfaceVariant, size: 18),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(panelRadius + 2),
        ),
      ),
      dividerTheme: DividerThemeData(color: scheme.outlineVariant, space: 1),
    );
  }
}
