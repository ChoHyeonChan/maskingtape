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
    'birth_date': '생년월일',
    'driver_license': '운전면허',
  };

  /// 라벨 맵에 이 kind가 있는지 — 코어에 새 탐지기가 추가됐는데 라벨을 안 넣은
  /// 상황을 테스트가 잡을 수 있게 남겨둔다.
  bool get hasLabel => _kindLabels.containsKey(kind);

  /// 라벨 맵에 없는 kind는 `기타(account)` 형태로 표시한다.
  ///
  /// 사용자에게는 읽을 수 있는 한국어("기타")가 보이고, 마스킹 자체는 코어가 이미
  /// 처리했으므로 결과에 영향이 없다. 괄호 안에 원래 kind를 남기는 이유는, 라벨
  /// 누락을 "기타"로 완전히 뭉뚱그리면 어떤 종류가 빠졌는지 알 수 없어져서다 —
  /// 실제로 card·biz_reg·passport·account가 이 표시 덕분에 발견됐다.
  String get kindLabel => _kindLabels[kind] ?? '기타($kind)';

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
