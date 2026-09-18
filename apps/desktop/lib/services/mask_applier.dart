import '../models/detection.dart';
import 'anonymizer.dart';

/// 탐지 구간을 항목별 가림/노출 선택에 따라 치환해 마스킹 결과 텍스트를 만든다.
///
/// 왜 앱에서 치환하는가: 항목별 「가림」 토글은 사용자가 고른 부분집합으로 결과를 다시
/// 만들어야 하는데, 코어 CLI/API에는 "이 탐지만 빼고"를 넘길 방법이 없다. 그래서 웹
/// 플레이그라운드(`apps/web/src/lib/masking.ts`)와 같은 방식으로 **치환만** 여기서 한다.
/// 탐지는 여전히 코어가 한다 — 이 파일은 코어가 준 구간을 코어와 같은 규칙으로 바꿀 뿐이다.
///
/// - `mask`: 같은 길이의 `*` — 코어 `MaskAnonymizer`와 동일
/// - `label`: `[주민등록번호]` 같은 종류 라벨 — 코어 `LabelAnonymizer`의 어휘와 동일
/// - `pseudonym`: 코어의 "그럴듯한 가짜 값" 생성이 필요해 여기서 만들 수 없다 →
///   [supports]가 false이고, 호출 측은 코어가 준 결과를 그대로 쓰며 항목별 조정을 끈다.
abstract final class MaskApplier {
  /// 코어 `anonymizers/label.py`의 라벨 어휘. 코어에 종류가 늘면 여기도 같이 늘린다 —
  /// 없는 kind는 웹과 같이 `[kind]`로 떨어져 눈에 띄게 한다.
  static const _labels = <String, String>{
    'rrn': '주민등록번호',
    'phone': '전화번호',
    'email': '이메일',
    'name': '이름',
    'address': '주소',
    'card': '카드번호',
    'account': '계좌번호',
    'biz_reg': '사업자등록번호',
    'passport': '여권번호',
    'birth_date': '생년월일',
    'driver_license': '운전면허',
  };

  static bool supports(MaskStrategy strategy) =>
      strategy != MaskStrategy.pseudonym;

  /// [detections] 중 [isMasked]가 true인 것만 치환한 텍스트.
  ///
  /// 겹치는 구간은 앞의 것을 우선하고 뒤의 것은 건너뛴다(코어 파이프라인이 겹침을
  /// 정리해 주지만 방어적으로 둔다). 노출로 고른 항목은 원문 그대로 남는다.
  static String apply(
    String text,
    List<Detection> detections, {
    required MaskStrategy strategy,
    required bool Function(Detection) isMasked,
  }) {
    assert(supports(strategy), 'pseudonym은 코어만 만들 수 있다');
    final ordered = [...detections]
      ..sort((a, b) => a.start != b.start ? a.start - b.start : b.end - a.end);
    final out = StringBuffer();
    var cursor = 0;
    for (final d in ordered) {
      if (d.start < cursor || d.end > text.length || d.start > d.end) continue;
      out.write(text.substring(cursor, d.start));
      out.write(
        isMasked(d) ? _segment(d, strategy) : text.substring(d.start, d.end),
      );
      cursor = d.end;
    }
    out.write(text.substring(cursor));
    return out.toString();
  }

  static String _segment(Detection d, MaskStrategy strategy) =>
      switch (strategy) {
        MaskStrategy.label => '[${_labels[d.kind] ?? d.kind}]',
        _ => '*' * (d.end - d.start),
      };
}
