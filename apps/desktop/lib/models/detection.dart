/// core의 Detection 타입(JSON)과 1:1 대응하는 데이터 클래스.
/// apps/api README의 API 계약 v1과 같은 스키마라 REST 전환 후에도 그대로 쓴다.
class Detection {
  const Detection({
    required this.kind,
    required this.start,
    required this.end,
    required this.text,
    this.confidence = 1.0,
    this.detector = '',
  });

  factory Detection.fromJson(Map<String, dynamic> json) => Detection(
        kind: json['kind'] as String,
        start: json['start'] as int,
        end: json['end'] as int,
        text: json['text'] as String,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
        detector: json['detector'] as String? ?? '',
      );

  final String kind;
  final int start;
  final int end;
  final String text;
  final double confidence;
  final String detector;

  static const _kindLabels = {
    'rrn': '주민번호',
    'phone': '전화번호',
    'email': '이메일',
    'name': '이름',
    'address': '주소',
    'card': '카드번호',
    'biz_reg': '사업자등록번호',
    'passport': '여권번호',
    'account': '계좌번호',
  };

  /// 코어가 라벨 맵에 없는 새 kind를 내보내면(예: 새 탐지기 추가) 한국어 대신
  /// `kind(?)`로 표시한다 — 사용자에게 원시 영어가 그대로 새는 대신,
  /// 개발 중 "라벨을 추가해야 한다"를 눈에 띄게 알린다.
  bool get hasLabel => _kindLabels.containsKey(kind);

  String get kindLabel => _kindLabels[kind] ?? '$kind(?)';

  /// "주민번호 1 · 전화번호 2" 식 종류별 개수 요약. 빈 목록이면 "탐지 없음".
  static String summarize(List<Detection> detections) {
    if (detections.isEmpty) {
      return '탐지 없음';
    }
    final counts = <String, int>{};
    for (final d in detections) {
      counts[d.kindLabel] = (counts[d.kindLabel] ?? 0) + 1;
    }
    return counts.entries.map((e) => '${e.key} ${e.value}').join(' · ');
  }
}
