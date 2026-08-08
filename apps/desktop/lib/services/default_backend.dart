import 'anonymizer.dart';
import 'cli_anonymizer.dart';
import 'fallback_anonymizer.dart';
import 'rest_anonymizer.dart';

/// 앱이 기본으로 쓰는 백엔드 조립 — 이 파일은 "무엇을 어떤 순서로 쓸지"만 정한다.
///
/// 로컬 CLI를 먼저 시도하고, 없으면 REST API로 넘어간다. 순서를 이렇게 둔 이유는
/// [FallbackAnonymizer] 주석 참고 — 요약하면 로컬이 기능도 많고(가명처리·LLM)
/// 텍스트가 PC를 벗어나지 않기 때문이다.
Anonymizer defaultAnonymizer() => FallbackAnonymizer([
      const CliAnonymizer(),
      RestAnonymizer(),
    ]);
