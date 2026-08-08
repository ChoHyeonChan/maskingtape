import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/fallback_anonymizer.dart';

import 'fakes.dart';

/// 닿지 못한 백엔드 — CLI 미설치·서버 미실행을 흉내 낸다.
class _UnavailableAnonymizer implements Anonymizer {
  const _UnavailableAnonymizer(this.message);

  final String message;

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async =>
      throw AnonymizerUnavailableException(message);
}

void main() {
  test('첫 백엔드가 되면 그대로 쓴다 — 뒤는 호출하지 않는다', () async {
    final first = FakeAnonymizer();
    final second = FakeAnonymizer();

    await FallbackAnonymizer([first, second])
        .anonymize('주민번호 ${FakeAnonymizer.rrn}');

    expect(first.lastOptions, isNotNull);
    expect(second.lastOptions, isNull, reason: '앞이 성공했으면 뒤는 부르지 않아야 한다');
  });

  test('첫 백엔드에 닿지 못하면 다음으로 넘어간다', () async {
    final rest = FakeAnonymizer();

    final result = await FallbackAnonymizer([
      const _UnavailableAnonymizer('CLI 없음'),
      rest,
    ]).anonymize('주민번호 ${FakeAnonymizer.rrn}');

    expect(rest.lastOptions, isNotNull);
    expect(result.detections.single.kind, 'rrn');
  });

  test('옵션은 넘겨받은 백엔드까지 그대로 전달된다', () async {
    final rest = FakeAnonymizer();

    await FallbackAnonymizer([
      const _UnavailableAnonymizer('CLI 없음'),
      rest,
    ]).anonymize(
      '이름 ${FakeAnonymizer.name}',
      options: const AnonymizeOptions(
        strategy: MaskStrategy.label,
        useLlm: true,
      ),
    );

    expect(rest.lastOptions?.strategy, MaskStrategy.label);
    expect(rest.lastOptions?.useLlm, isTrue);
  });

  test('처리 중 오류는 넘기지 않고 그대로 올린다', () async {
    final second = FakeAnonymizer();

    await expectLater(
      FallbackAnonymizer([
        const FailingAnonymizer(message: 'Ollama가 실행 중이지 않습니다'),
        second,
      ]).anonymize('x'),
      throwsA(isA<AnonymizerException>().having(
        (e) => e.message,
        'message',
        'Ollama가 실행 중이지 않습니다',
      )),
    );
    expect(
      second.lastOptions,
      isNull,
      reason: '백엔드를 바꿔도 같은 결과라, 넘기면 원인만 가려진다',
    );
  });

  test('전부 닿지 못하면 사유를 모두 담아 알린다', () async {
    await expectLater(
      FallbackAnonymizer([
        const _UnavailableAnonymizer('CLI를 찾을 수 없습니다'),
        const _UnavailableAnonymizer('API 서버에 연결할 수 없습니다'),
      ]).anonymize('x'),
      throwsA(isA<AnonymizerUnavailableException>().having(
        (e) => e.message,
        'message',
        allOf(contains('CLI를 찾을 수 없습니다'), contains('API 서버에 연결할 수 없습니다')),
      )),
    );
  });
}
