import '../models/detection.dart';

/// 비식별화 호출 결과 — 마스킹된 텍스트와 탐지 목록.
class AnonymizeResult {
  const AnonymizeResult({required this.maskedText, required this.detections});

  final String maskedText;
  final List<Detection> detections;
}

/// 비식별화 백엔드 인터페이스.
/// 지금은 core CLI(CliAnonymizer), apps/api 완성 후 REST 구현으로 교체한다.
abstract interface class Anonymizer {
  Future<AnonymizeResult> anonymize(String text);
}

/// 백엔드 호출 실패 (CLI 없음, 비정상 종료 등).
class AnonymizerException implements Exception {
  const AnonymizerException(this.message);

  final String message;

  @override
  String toString() => message;
}
