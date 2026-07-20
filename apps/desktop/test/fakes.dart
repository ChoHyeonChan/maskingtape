import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';

/// CLI 없이 테스트하기 위한 가짜 백엔드 — 주민번호 하나를 찾은 척한다.
class FakeAnonymizer implements Anonymizer {
  FakeAnonymizer();

  /// 마지막 호출에 쓰인 전략 — 전략 전달 검증용.
  MaskStrategy? lastStrategy;

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    MaskStrategy strategy = MaskStrategy.mask,
  }) async {
    lastStrategy = strategy;
    final replacement =
        strategy == MaskStrategy.label ? '[주민등록번호]' : '**************';
    return AnonymizeResult(
      maskedText: text.replaceAll('800101-1234560', replacement),
      detections: [
        if (text.contains('800101-1234560'))
          Detection(
            kind: 'rrn',
            start: text.indexOf('800101-1234560'),
            end: text.indexOf('800101-1234560') + 14,
            text: '800101-1234560',
          ),
      ],
    );
  }
}

/// 항상 실패하는 백엔드 — 오류 표시 검증용.
class FailingAnonymizer implements Anonymizer {
  const FailingAnonymizer();

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    MaskStrategy strategy = MaskStrategy.mask,
  }) async =>
      throw const AnonymizerException('테스트용 실패');
}
