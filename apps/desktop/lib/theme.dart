// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';

/// 마스킹테이프 브랜드 테마 — 웹 플레이그라운드와 같은 팔레트.
///
/// 설계 근거(왜 이렇게 골랐는지 — 리뷰 시 이 문단부터 보면 된다):
///
/// 산출물이 다섯(CLI·MCP·API·웹·데스크톱)인데 사용자가 **눈으로 보는** 건 웹과
/// 데스크톱 둘뿐이다. 이 둘이 다른 색을 쓰면 같은 제품으로 읽히지 않는다 — 발표에서
/// 나란히 띄우는 순간 드러난다. 그래서 데스크톱만의 팔레트(노란 테이프 + 검정)를
/// 버리고 **웹 `apps/web/src/styles/tokens.css`의 값을 그대로 옮겼다**(#442).
/// 토큰 이름도 웹과 맞춰 두었으니, 웹이 바뀌면 여기 상수만 같이 고치면 된다.
///
/// 테이프 모티프([tape])는 남긴다 — 이름이 마스킹테이프인 도구가 화면에서 테이프를
/// 보여주지 않으면 이름이 붕 뜬다. 다만 색은 **로고의 파란 테이프 롤**과 같은 브랜드
/// 남색이다. "가려진 자리 = 테이프가 붙은 자리 = 완료"라는 뜻은 그대로다.
///
/// 색이 셋뿐인 원칙도 유지한다: 남색(브랜드·완료·강조), 회색(대기·처리 중·보조),
/// 빨강(실패에만). 탐지 종류별 색은 결과 미리보기 안에서만 쓴다(`kind_colors.dart`).
///
/// 글꼴은 시스템 글꼴을 그대로 쓴다. 웹도 `Inter, "Segoe UI", system-ui` 폴백 체인이라
/// 폰트 파일을 싣지 않는다 — Windows에선 둘 다 Segoe UI + 맑은 고딕으로 렌더된다.
/// 한글 글꼴을 번들하려면 라이선스 확인과 SBOM 등록이 필요한데(§2-2), 팀 허용
/// 목록(MIT/Apache/BSD/ISC)에 흔한 한글 글꼴 라이선스(OFL)가 없다.
abstract final class AppTheme {
  // ─── 브랜드 (웹 tokens.css --brand-*) ────────────────────
  /// 브랜드 남색 — 로고·선택된 세그먼트·완료 칩·테이프. 웹 `--brand-blue`.
  static const brand = Color(0xFF183A8B);

  /// 브랜드 남색의 짙은 면 — 테이프 테두리·강조 글자. 웹 `--brand-blue-deep`.
  static const brandDeep = Color(0xFF102A68);

  /// 브랜드 남색을 옅게 깐 면 — 칩 배경·드롭 호버. 웹 `--brand-blue-soft`.
  static const brandSoft = Color(0xFFE8EEFB);

  /// 가장 옅은 브랜드 면 — 배지 배경. 웹 `--brand-blue-tint`.
  static const brandTint = Color(0xFFF5F8FE);

  /// 행동 버튼 파랑 — "탐지 실행"·"비식별화 시작" 같은 주 버튼 하나에만.
  /// 웹 `.input-panel__primary`의 `#0b55f0`.
  static const action = Color(0xFF0B55F0);

  // ─── 테이프 — 브랜드색의 별칭 ───────────────────────────
  // 이름을 남겨 두는 이유: 위젯 쪽에서 "테이프 색"이라고 읽히는 게 의도를 보존한다.
  // 값은 로고의 파란 테이프 롤과 같다.
  static const tape = brand;
  static const tapeDeep = brandDeep;
  static const tapeSoft = brandSoft;

  // ─── 바탕·글자 (웹 --surface, --text-*) ──────────────────
  /// 창 바탕 — 웹 `body` 배경 `#f6f8fb`.
  static const surface = Color(0xFFF6F8FB);

  /// 패널·카드 면 — 웹 `--surface-strong`.
  static const surfaceStrong = Color(0xFFFFFFFF);

  /// 본문 글자 — 웹 `--text-primary`.
  static const textPrimary = Color(0xFF10203D);

  /// 보조 글자 — 웹 `--text-secondary`.
  static const textSecondary = Color(0xFF4B5F7D);

  /// 패널 테두리 — 웹 `.panel`의 `rgba(24,58,139,.18)`.
  static const border = Color(0x2E183A8B);

  /// 옅은 테두리 — 행·칩. 웹 `--border`(`rgba(24,58,139,.14)`).
  static const borderSoft = Color(0x24183A8B);

  /// 드롭존 점선 — 웹의 스크롤바 색과 같은 톤(`#91a2c9`).
  static const dashedLine = Color(0xFF91A2C9);

  // ─── 다크 ───────────────────────────────────────────────
  // 웹은 라이트 전용(`color-scheme: light`)이지만 데스크톱은 OS 설정을 따르므로
  // 같은 남색 계열로 어두운 면을 둔다.
  static const surfaceDark = Color(0xFF0F1730);
  static const surfaceStrongDark = Color(0xFF162040);
  static const borderDark = Color(0xFF2A3A66);

  // ─── 상태 ───────────────────────────────────────────────
  // 완료만 브랜드색이다 — "테이프가 붙었다"가 곧 완료라서.
  static const doneBg = brandSoft;
  static const doneFg = brand;
  static const runBg = Color(0xFFEEF1F6);
  static const runFg = textSecondary;
  static const waitBg = Color(0xFFF0F3F8);
  static const waitFg = textSecondary;

  /// 실패 — 웹 안내 말풍선과 같은 빨강(`#dc2626` / `#fde3e7`).
  static const failBg = Color(0xFFFDE3E7);
  static const failFg = Color(0xFFDC2626);

  /// 모서리 — 웹 `.panel` 14px, 버튼·세그먼트 8px.
  static const panelRadius = 14.0;
  static const controlRadius = 8.0;

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(seedColor: brand).copyWith(
      primary: brand,
      onPrimary: Colors.white,
      secondary: action,
      onSecondary: Colors.white,
      surface: surfaceStrong,
      onSurface: textPrimary,
      onSurfaceVariant: textSecondary,
      outlineVariant: border,
      error: failFg,
    );
    return _base(scheme, scaffold: surface);
  }

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: brand,
      brightness: Brightness.dark,
    ).copyWith(
      primary: const Color(0xFFB9C8F2),
      onPrimary: brandDeep,
      secondary: const Color(0xFF6E9BFF),
      onSecondary: Colors.white,
      surface: surfaceStrongDark,
      onSurface: const Color(0xFFE6EBF7),
      onSurfaceVariant: const Color(0xFF9DAAC9),
      outlineVariant: borderDark,
    );
    return _base(scheme, scaffold: surfaceDark);
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
      // 웹과 같은 굵기 체계 — 제목 800, 라벨 700~800, 본문 400.
      textTheme: const TextTheme(
        displaySmall: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w800,
          letterSpacing: -1.1,
        ),
        titleLarge: TextStyle(
          fontSize: 19,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.4,
        ),
        titleMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
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
        labelLarge: TextStyle(fontWeight: FontWeight.w800),
      ),
      // 주 버튼은 웹 CTA와 같은 파랑 — 한 화면에 하나뿐이라 세게 써도 된다.
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: scheme.secondary,
          foregroundColor: scheme.onSecondary,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: scheme.onSurface,
          side: BorderSide(color: scheme.outlineVariant),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: scheme.primary),
      ),
      // 웹 `.input-panel__mask-mode` — 선택된 칸만 남색, 나머지는 흰 바탕에 보조 글자.
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          backgroundColor: scheme.surface,
          foregroundColor: scheme.onSurfaceVariant,
          selectedBackgroundColor: scheme.primary,
          selectedForegroundColor: scheme.onPrimary,
          side: BorderSide(color: scheme.outlineVariant),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius),
          ),
        ),
      ),
      // 진행률은 테이프가 깔리는 것으로 읽히게 — 색을 테이프(브랜드)로 고정한다.
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
          fontWeight: FontWeight.w700,
          fontSize: 13,
        ),
        iconTheme: IconThemeData(color: scheme.onSurfaceVariant, size: 18),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(panelRadius),
        ),
      ),
      dividerTheme: DividerThemeData(color: scheme.outlineVariant, space: 1),
    );
  }
}
