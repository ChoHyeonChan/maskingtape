// 실제로 실행 중인 apps/api에 붙여보는 수동 확인용 스크립트.
// 자동 테스트가 아니다 — 서버가 떠 있어야 하므로 `flutter test`에 포함되지 않는다.
//
//   python -m uvicorn maskingtape_api.main:app --port 8000
//   dart run test/manual_rest_smoke.dart
import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/default_backend.dart';
import 'package:maskingtape_desktop/services/rest_anonymizer.dart';

// 전부 합성(가짜) 값이다.
const _sample = '김민서 고객님 연락처 010-1234-5678, 계좌 123456-01-123456, '
    '여권 M12345678, 사업자 100-00-00009 입니다.';

Future<void> _try(String label, Anonymizer backend, AnonymizeOptions options) async {
  try {
    final result = await backend.anonymize(_sample, options: options);
    print('[$label] ${result.maskedText}');
    print('        ${Detection.summarize(result.detections)}');
  } on AnonymizerException catch (e) {
    print('[$label] 실패: ${e.message}');
  }
}

Future<void> main() async {
  final rest = RestAnonymizer();
  await _try('REST mask  ', rest, const AnonymizeOptions());
  await _try('REST label ', rest, const AnonymizeOptions(strategy: MaskStrategy.label));
  await _try('REST 가명   ', rest, const AnonymizeOptions(strategy: MaskStrategy.pseudonym));
  await _try('REST LLM   ', rest, const AnonymizeOptions(useLlm: true));
  // 기본 조립 — 이 PC에 CLI가 없으면 REST로 넘어간다.
  await _try('기본 백엔드 ', defaultAnonymizer(), const AnonymizeOptions());
}
