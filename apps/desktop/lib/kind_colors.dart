import 'package:flutter/material.dart';

/// 탐지 종류(kind)별 강조색 — 웹 `tokens.css`의 `--kind-*`와 같은 값.
///
/// 결과 미리보기에서 "무엇이 잡혔는지"를 색으로 구분할 때만 쓴다. 웹의 탐지 목록
/// 점(dot)·하이라이트와 같은 색이라, 두 표면을 오가는 사람이 색만 보고도 종류를
/// 알아본다. 화면 나머지(버튼·칩·테이프)는 브랜드 남색 하나로 통일한다(`theme.dart`).
///
/// 모르는 kind는 중립 회색으로 — 코어에 탐지기가 추가됐는데 여기 색이 없을 때
/// 눈에 띄게 튀지 않으면서 "정보 없음"으로 읽히게 한다(웹 `--kind-fallback`과 동일).
abstract final class KindColors {
  static const _byKind = <String, Color>{
    'rrn': Color(0xFF183A8B),
    'passport': Color(0xFF3158B7),
    'phone': Color(0xFF16806F),
    'email': Color(0xFFB83B75),
    'card': Color(0xFFB9671D),
    'address': Color(0xFF6751B8),
    'name': Color(0xFF0F6F7D),
    'biz_reg': Color(0xFF167F9F),
    // 웹에 아직 없는 종류는 가까운 계열에서 골랐다 — 계좌는 카드와 같은 재무 계열,
    // 생년월일·운전면허는 주민번호와 같은 신원 계열.
    'account': Color(0xFF9A5A1A),
    'birth_date': Color(0xFF2F4FA8),
    'driver_license': Color(0xFF4A63B0),
  };

  static const fallback = Color(0xFF8A94A5);

  /// kind에 대응하는 글자·점 색.
  static Color of(String kind) => _byKind[kind] ?? fallback;

  /// 하이라이트 배경 — 웹 `.highlight`처럼 종류색을 옅게(35%) 깐다.
  static Color backgroundOf(String kind) => of(kind).withValues(alpha: 0.16);
}
