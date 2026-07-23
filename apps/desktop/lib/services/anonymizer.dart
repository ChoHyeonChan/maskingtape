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

/// 비식별화 호출 옵션.
/// 옵션이 늘어도 백엔드 구현들의 시그니처가 흔들리지 않도록 객체로 묶는다.
class AnonymizeOptions {
  const AnonymizeOptions({
    this.strategy = MaskStrategy.mask,
    this.useLlm = false,
  });

  final MaskStrategy strategy;

  /// 이름을 규칙 대신 로컬 LLM으로 판단할지 (CLI `--llm`).
  /// 켜려면 실행 PC에 Ollama가 떠 있어야 한다.
  final bool useLlm;

  AnonymizeOptions copyWith({MaskStrategy? strategy, bool? useLlm}) =>
      AnonymizeOptions(
        strategy: strategy ?? this.strategy,
        useLlm: useLlm ?? this.useLlm,
      );
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
    AnonymizeOptions options = const AnonymizeOptions(),
  });
}

/// 백엔드 호출 실패 (CLI 없음, 비정상 종료, Ollama 미실행 등).
class AnonymizerException implements Exception {
  const AnonymizerException(this.message);

  final String message;

  @override
  String toString() => message;
}
