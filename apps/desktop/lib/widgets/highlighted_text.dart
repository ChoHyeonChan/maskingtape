import 'package:flutter/material.dart';

import '../kind_colors.dart';
import '../models/detection.dart';

/// 원문에 탐지 구간을 종류별 색으로 칠해 보여주는 선택 가능한 텍스트.
///
/// 결과 미리보기 다이얼로그(파일 모드)와 텍스트 입력 모드가 같은 위젯을 쓴다 —
/// 하이라이트 규칙이 두 군데서 따로 놀면 같은 문장이 다르게 보인다.
class HighlightedText extends StatelessWidget {
  const HighlightedText({
    super.key,
    required this.text,
    required this.detections,
    this.style,
  });

  final String text;
  final List<Detection> detections;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    return SelectableText.rich(
      TextSpan(
        style: style ?? Theme.of(context).textTheme.bodyMedium,
        children: buildSpans(text, detections),
      ),
    );
  }

  /// 원문을 탐지 구간 기준으로 잘라, 탐지된 부분에 종류별 색 하이라이트를 입힌다.
  ///
  /// 겹치거나 범위를 벗어난 탐지는 건너뛴다 — 원문이 처리 후 바뀌었거나 백엔드가
  /// 겹침을 정리하지 않았을 때 앱이 죽지 않게 한다.
  static List<TextSpan> buildSpans(String text, List<Detection> detections) {
    final ordered = [...detections]..sort((a, b) => a.start - b.start);
    final spans = <TextSpan>[];
    var cursor = 0;
    for (final d in ordered) {
      if (d.start < cursor || d.end > text.length || d.start > d.end) {
        continue;
      }
      if (d.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, d.start)));
      }
      spans.add(
        TextSpan(
          text: text.substring(d.start, d.end),
          // 웹 결과 화면과 같은 종류별 색 — 주민번호는 남색, 전화는 초록, 이메일은
          // 자주… 두 표면을 오가도 색만 보고 종류를 알아본다(kind_colors.dart).
          style: TextStyle(
            backgroundColor: KindColors.backgroundOf(d.kind),
            color: KindColors.of(d.kind),
            fontWeight: FontWeight.w700,
          ),
        ),
      );
      cursor = d.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }
}
