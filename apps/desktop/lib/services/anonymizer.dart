import '../models/detection.dart';

/// 비식별화 전략 — API 계약 v1의 strategy 필드와 1:1.
enum MaskStrategy {
  /// `*`로 가림 (기본)
  mask('mask', '가리기 (***)'),

  /// `[전화번호]` 식 라벨 치환 — 정보 종류가 보존된다
  label('label', '라벨 ([전화번호])');

  const MaskStrategy(this.wireName, this.displayName);

  /// CLI `--strategy` 값이자 API 요청의 strategy 값.
  final String wireName;
  final String displayName;
}

/// 비식별화 호출 결과 — 마스킹된 텍스트와 탐지 목록.
class AnonymizeResult {
  const AnonymizeResult({required this.maskedText, required this.detections});

  final String maskedText;
  final List<Detection> detections;
}

/// 비식별화 백엔드 인터페이스.
/// 지금은 core CLI(CliAnonymizer), apps/api 완성 후 REST 구현으로 교체한다.
abstract interface class Anonymizer {
  Future<AnonymizeResult> anonymize(
    String text, {
    MaskStrategy strategy = MaskStrategy.mask,
  });
}

/// 백엔드 호출 실패 (CLI 없음, 비정상 종료 등).
class AnonymizerException implements Exception {
  const AnonymizerException(this.message);

  final String message;

  @override
  String toString() => message;
}
