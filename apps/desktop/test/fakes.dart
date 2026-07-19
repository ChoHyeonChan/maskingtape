import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';

/// CLI 없이 테스트하기 위한 가짜 백엔드 — 주민번호 하나를 찾은 척한다.
class FakeAnonymizer implements Anonymizer {
  const FakeAnonymizer();

  @override
  Future<AnonymizeResult> anonymize(String text) async => AnonymizeResult(
        maskedText: text.replaceAll('800101-1234560', '**************'),
        detections: [
          if (text.contains('800101-1234560'))
            const Detection(
              kind: 'rrn',
              start: 0,
              end: 14,
              text: '800101-1234560',
            ),
        ],
      );
}

/// 항상 실패하는 백엔드 — 오류 표시 검증용.
class FailingAnonymizer implements Anonymizer {
  const FailingAnonymizer();

  @override
  Future<AnonymizeResult> anonymize(String text) async =>
      throw const AnonymizerException('테스트용 실패');
}
