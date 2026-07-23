import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';

/// CLI 없이 테스트하기 위한 가짜 백엔드.
/// 합성 주민번호를 찾은 척하고, LLM 모드면 합성 이름도 찾은 척한다.
class FakeAnonymizer implements Anonymizer {
  FakeAnonymizer();

  /// 마지막 호출에 쓰인 옵션 — 전달 검증용.
  AnonymizeOptions? lastOptions;

  static const rrn = '800101-1234560'; // 체크섬만 맞춘 합성 번호
  static const name = '김민서'; // 합성 이름

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async {
    lastOptions = options;
    final isLabel = options.strategy == MaskStrategy.label;
    var masked = text;
    final detections = <Detection>[];

    if (text.contains(rrn)) {
      detections.add(
        Detection(
          kind: 'rrn',
          start: text.indexOf(rrn),
          end: text.indexOf(rrn) + rrn.length,
          text: rrn,
        ),
      );
      masked = masked.replaceAll(rrn, isLabel ? '[주민등록번호]' : '*' * rrn.length);
    }
    // 이름은 LLM 모드에서만 찾는다 — 규칙 전용 모드와의 차이를 검증할 수 있게.
    if (options.useLlm && text.contains(name)) {
      detections.add(
        Detection(
          kind: 'name',
          start: text.indexOf(name),
          end: text.indexOf(name) + name.length,
          text: name,
          confidence: 0.9,
        ),
      );
      masked = masked.replaceAll(name, isLabel ? '[이름]' : '*' * name.length);
    }

    return AnonymizeResult(maskedText: masked, detections: detections);
  }
}

/// 항상 실패하는 백엔드 — 오류 표시 검증용.
class FailingAnonymizer implements Anonymizer {
  const FailingAnonymizer({this.message = '테스트용 실패'});

  final String message;

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async =>
      throw AnonymizerException(message);
}
