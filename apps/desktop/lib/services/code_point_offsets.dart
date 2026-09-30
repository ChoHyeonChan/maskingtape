// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import '../models/detection.dart';
import 'anonymizer.dart';

/// core가 주는 탐지 위치(코드포인트)를 Dart 문자열 위치(UTF-16 코드 유닛)로 바꾼다.
///
/// 왜 필요한가(#496): core는 파이썬 문자열 위치를 준다 — 글자 하나가 한 칸이다. Dart
/// `String`의 `substring`·`length`는 UTF-16 코드 유닛 기준이라, 이모지처럼 BMP 밖 글자는
/// 두 칸을 차지한다. 개인정보 앞에 이모지가 k개 있으면 core 위치를 그대로 쓸 때 가림
/// 구간이 k칸 앞으로 밀리고 **개인정보 끝 k글자가 원문으로 남는다**(k=14면 주민번호 전체).
///
/// 그래서 위치가 앱에 들어오는 두 곳(CLI·REST)에서 **한 번만** 바꾼다. 그 뒤로는 앱의
/// 모든 코드(결과·복사·하이라이트·파일 미리보기)가 Dart 기준 위치를 쓰므로, 쓰는 곳마다
/// 따로 바꾸다 한 군데를 빠뜨리는 일이 생기지 않는다.
class CodePointOffsets {
  CodePointOffsets(this._text) : _utf16At = _build(_text);

  final String _text;

  /// `_utf16At[i]` = i번째 코드포인트가 시작하는 UTF-16 위치. 끝 위치(코드포인트 개수)도
  /// 담아 두어 구간 끝(`end`)을 바로 찾을 수 있다.
  final List<int> _utf16At;

  static List<int> _build(String text) {
    final table = <int>[];
    var unit = 0;
    for (final rune in text.runes) {
      table.add(unit);
      unit += rune > 0xFFFF ? 2 : 1; // BMP 밖(서로게이트 쌍)은 두 칸
    }
    table.add(unit);
    return table;
  }

  /// 원문의 코드포인트 개수.
  int get codePointLength => _utf16At.length - 1;

  /// core 위치 하나를 UTF-16 위치로. 범위를 벗어나면 [AnonymizerException].
  int toUtf16(int codePoint) {
    if (codePoint < 0 || codePoint >= _utf16At.length) {
      // core와 앱이 서로 다른 텍스트를 보고 있다는 뜻이다. 어긋난 위치로 가리면 엉뚱한
      // 글자를 가리고 개인정보를 남길 수 있으니, 조용히 넘기지 않고 처리 실패로 알린다.
      throw const AnonymizerException('탐지 위치가 원문 범위를 벗어났습니다. 다시 시도해 주세요.');
    }
    return _utf16At[codePoint];
  }

  /// 탐지 목록의 위치를 모두 UTF-16으로 바꾼 새 목록.
  ///
  /// 탐지 값(`text`)이 비어 있으면 원문에서 잘라 채운다 — API는 원문 반향을 막으려고 값을
  /// 보내지 않는다(#497). 원문은 이미 이 PC에 있으니 네트워크로 되돌려 받을 필요가 없다.
  List<Detection> convert(List<Detection> detections) => [
    for (final d in detections) _convertOne(d),
  ];

  Detection _convertOne(Detection d) {
    final start = toUtf16(d.start);
    final end = toUtf16(d.end);
    return d.withOffsets(
      start: start,
      end: end,
      text: d.text.isEmpty ? _text.substring(start, end) : null,
    );
  }
}
