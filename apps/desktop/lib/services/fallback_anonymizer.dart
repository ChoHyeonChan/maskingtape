import 'anonymizer.dart';

/// 백엔드를 순서대로 시도하는 조합 구현 — 자신은 비식별화를 하지 않는다.
///
/// 기본 순서는 **로컬 CLI 먼저, REST API 나중**이다:
/// - 로컬 CLI는 가명처리·이름 정밀 탐지(LLM)까지 전부 되고, 텍스트가 이 PC를 벗어나지
///   않는다 — "진짜 개인정보는 로컬에서 처리하세요"라는 제품 메시지와 맞는다.
/// - CLI가 깔려 있지 않은 PC(설치 없이 실행한 배포판)에서는 API로 넘어가 동작한다.
///
/// [AnonymizerUnavailableException]일 때만 다음 백엔드로 넘긴다. 처리 중 발생한
/// 오류는 백엔드를 바꿔도 같은 결과라, 넘기면 원인만 가려진다.
class FallbackAnonymizer implements Anonymizer {
  const FallbackAnonymizer(this.backends) : assert(backends.length > 0);

  /// 시도할 순서대로의 백엔드 목록.
  final List<Anonymizer> backends;

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async {
    final reasons = <String>[];

    for (final backend in backends) {
      try {
        return await backend.anonymize(text, options: options);
      } on AnonymizerUnavailableException catch (e) {
        reasons.add(e.message);
      }
    }

    // 전부 닿지 못했다. 한쪽 사유만 보여주면 "CLI를 깔라"와 "서버를 켜라" 중
    // 하나가 가려지므로, 사용자가 고를 수 있게 둘 다 보여준다.
    throw AnonymizerUnavailableException(
      '비식별화 백엔드에 연결하지 못했습니다 — ${reasons.join(' / ')}',
    );
  }
}
