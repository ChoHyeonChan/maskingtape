import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/cli_anonymizer.dart';

void main() {
  group('argsFor', () {
    test('기본: 탐지는 --scan, 마스킹은 --strategy mask', () {
      const options = AnonymizeOptions();

      expect(CliAnonymizer.argsFor(options, scan: true), ['--scan']);
      expect(
        CliAnonymizer.argsFor(options, scan: false),
        ['--strategy', 'mask'],
      );
    });

    test('label 전략이 CLI 값으로 전달된다', () {
      const options = AnonymizeOptions(strategy: MaskStrategy.label);

      expect(
        CliAnonymizer.argsFor(options, scan: false),
        ['--strategy', 'label'],
      );
    });

    test('LLM 모드는 탐지·마스킹 두 호출 모두에 --llm이 붙는다', () {
      // 한쪽에만 붙으면 화면의 탐지 요약과 저장된 결과의 기준이 어긋난다.
      const options = AnonymizeOptions(useLlm: true);

      expect(CliAnonymizer.argsFor(options, scan: true), contains('--llm'));
      expect(CliAnonymizer.argsFor(options, scan: false), contains('--llm'));
    });

    test('LLM을 끄면 --llm을 보내지 않는다 (Ollama 없이도 동작)', () {
      const options = AnonymizeOptions(useLlm: false);

      expect(
        CliAnonymizer.argsFor(options, scan: true),
        isNot(contains('--llm')),
      );
      expect(
        CliAnonymizer.argsFor(options, scan: false),
        isNot(contains('--llm')),
      );
    });
  });
}
