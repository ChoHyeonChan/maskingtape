import 'dart:convert';
import 'dart:io';

import '../models/detection.dart';
import 'anonymizer.dart';

/// apps/api REST 백엔드(`POST /anonymize`)를 호출하는 구현.
///
/// CLI 구현과 달리 호출이 한 번이다 — API 계약 v1의 `/anonymize` 응답이
/// 마스킹된 텍스트와 탐지 목록을 함께 주기 때문이다.
///
/// HTTP는 `dart:io`의 HttpClient로 직접 다룬다. 단순한 JSON POST 하나뿐이라
/// 패키지를 추가할 이유가 없고, 의존성이 늘면 SBOM 관리 부담만 커진다.
class RestAnonymizer implements Anonymizer {
  RestAnonymizer({
    Uri? baseUrl,
    HttpClient? client,
    this.timeout = const Duration(seconds: 30),
  })  : baseUrl = baseUrl ?? Uri.parse(defaultBaseUrl),
        _client = client ?? HttpClient();

  /// 개발용 기본 주소 — apps/api README의 로컬 실행 주소와 같다.
  static const defaultBaseUrl = 'http://127.0.0.1:8000';

  final Uri baseUrl;
  final Duration timeout;
  final HttpClient _client;

  /// API가 처리할 수 있는 요청인지.
  ///
  /// 배포판 API는 규칙 기반 탐지만 제공하고(로컬 Ollama가 필요한 `--llm` 제외),
  /// `/anonymize`의 strategy도 mask·label 두 가지만 받는다. 나머지는 CLI 경로로
  /// 처리해야 하므로, 호출 전에 이 조건으로 걸러 라우팅에 쓴다.
  static bool supports(AnonymizeOptions options) =>
      !options.useLlm && options.strategy != MaskStrategy.pseudonym;

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async {
    if (!supports(options)) {
      throw AnonymizerException(_unsupportedMessage(options));
    }

    final body = await _post('/anonymize', {
      'text': text,
      'strategy': options.strategy.wireName,
    });

    return AnonymizeResult(
      maskedText: body['text'] as String,
      detections: (body['detections'] as List<dynamic>)
          .map((e) => Detection.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, Object?> payload) async {
    final uri = baseUrl.resolve(path);
    final HttpClientResponse response;
    final String raw;
    try {
      final request = await _client.postUrl(uri).timeout(timeout);
      request.headers.contentType = ContentType('application', 'json', charset: 'utf-8');
      request.add(utf8.encode(jsonEncode(payload)));
      response = await request.close().timeout(timeout);
      raw = await response.transform(utf8.decoder).join().timeout(timeout);
    } on SocketException {
      // 서버에 닿지 못한 것뿐이므로 다른 백엔드로 넘길 수 있다.
      throw AnonymizerUnavailableException(
        'API 서버에 연결할 수 없습니다 ($uri) — 서버가 실행 중인지 확인하세요',
      );
    } on HttpException catch (e) {
      throw AnonymizerException('API 통신에 실패했습니다: ${e.message}');
    } catch (e) {
      // 타임아웃 등 — 서버는 떠 있을 수 있으므로 unavailable로 보지 않는다.
      throw AnonymizerException('API 호출이 실패했습니다 ($uri): $e');
    }

    if (response.statusCode != HttpStatus.ok) {
      throw AnonymizerException(_errorMessage(response.statusCode, raw));
    }
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  /// API가 준 에러 문구를 그대로 보여준다 — 무엇을 고쳐야 하는지는 서버가 안다.
  /// 계약상 에러 본문은 `{code, message, details}` 형식이다.
  static String _errorMessage(int statusCode, String raw) {
    try {
      final body = jsonDecode(raw) as Map<String, dynamic>;
      final message = body['message'];
      if (message is String && message.isNotEmpty) {
        return 'API 오류 ($statusCode): $message';
      }
    } on FormatException {
      // JSON이 아니면 아래 기본 문구로 떨어진다.
    }
    return 'API 오류 ($statusCode)';
  }

  static String _unsupportedMessage(AnonymizeOptions options) {
    if (options.useLlm) {
      return '이름 정밀 탐지(로컬 LLM)는 API 백엔드가 지원하지 않습니다 — '
          'maskingtape CLI를 설치하면 이 PC에서 처리할 수 있습니다';
    }
    return '${options.strategy.displayName} 전략은 API 백엔드가 지원하지 않습니다 — '
        'maskingtape CLI를 설치하면 이 PC에서 처리할 수 있습니다';
  }
}
