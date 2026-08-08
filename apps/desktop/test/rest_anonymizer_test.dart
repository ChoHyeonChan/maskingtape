import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/rest_anonymizer.dart';

/// 실제 HTTP 서버를 루프백에 띄워서 검증한다.
/// HttpClient를 가짜로 대체하면 요청 조립·인코딩·에러 매핑이 통째로 안 돌아
/// "테스트는 통과하는데 실제로는 안 되는" 상태가 되기 쉽다.
Future<HttpServer> _serve(
  Future<void> Function(HttpRequest request) handle,
) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    await handle(request);
    await request.response.close();
  });
  return server;
}

Uri _baseOf(HttpServer server) =>
    Uri.parse('http://${server.address.address}:${server.port}');

void main() {
  group('supports', () {
    test('mask·label은 API로 보낼 수 있다', () {
      expect(RestAnonymizer.supports(const AnonymizeOptions()), isTrue);
      expect(
        RestAnonymizer.supports(
          const AnonymizeOptions(strategy: MaskStrategy.label),
        ),
        isTrue,
      );
    });

    test('가명처리와 LLM 모드는 API가 지원하지 않는다', () {
      expect(
        RestAnonymizer.supports(
          const AnonymizeOptions(strategy: MaskStrategy.pseudonym),
        ),
        isFalse,
      );
      expect(
        RestAnonymizer.supports(const AnonymizeOptions(useLlm: true)),
        isFalse,
      );
    });
  });

  group('anonymize', () {
    test('요청 본문을 계약대로 보내고 응답을 결과로 옮긴다', () async {
      Map<String, dynamic>? received;
      final server = await _serve((request) async {
        received = jsonDecode(await utf8.decoder.bind(request).join())
            as Map<String, dynamic>;
        request.response
          ..statusCode = HttpStatus.ok
          ..headers.contentType = ContentType.json
          ..add(utf8.encode(jsonEncode({
            'text': '연락처 [전화번호]',
            'detections': [
              {
                'kind': 'phone',
                'start': 4,
                'end': 17,
                'text': '010-1234-5678',
                'confidence': 1.0,
                'detector': 'PhoneDetector',
              }
            ],
          })));
      });
      addTearDown(() => server.close(force: true));

      final result = await RestAnonymizer(baseUrl: _baseOf(server)).anonymize(
        '연락처 010-1234-5678',
        options: const AnonymizeOptions(strategy: MaskStrategy.label),
      );

      expect(received, {'text': '연락처 010-1234-5678', 'strategy': 'label'});
      expect(result.maskedText, '연락처 [전화번호]');
      expect(result.detections.single.kindLabel, '전화번호');
    });

    test('한글이 UTF-8로 온전히 왕복한다', () async {
      final server = await _serve((request) async {
        final body = jsonDecode(await utf8.decoder.bind(request).join())
            as Map<String, dynamic>;
        request.response
          ..statusCode = HttpStatus.ok
          ..add(utf8.encode(jsonEncode({
            'text': body['text'],
            'detections': <dynamic>[],
          })));
      });
      addTearDown(() => server.close(force: true));

      final result = await RestAnonymizer(baseUrl: _baseOf(server))
          .anonymize('주소는 서울특별시 중구입니다');

      expect(result.maskedText, '주소는 서울특별시 중구입니다');
    });

    test('API 에러 본문의 message를 그대로 보여준다', () async {
      final server = await _serve((request) async {
        request.response
          ..statusCode = HttpStatus.badRequest
          ..add(utf8.encode(jsonEncode({
            'code': 'invalid_request',
            'message': 'request body validation failed.',
            'details': null,
          })));
      });
      addTearDown(() => server.close(force: true));

      await expectLater(
        RestAnonymizer(baseUrl: _baseOf(server)).anonymize('x'),
        throwsA(
          isA<AnonymizerException>().having(
            (e) => e.message,
            'message',
            contains('request body validation failed.'),
          ),
        ),
      );
    });

    test('JSON이 아닌 에러 응답도 상태 코드로 안내한다', () async {
      final server = await _serve((request) async {
        request.response
          ..statusCode = HttpStatus.internalServerError
          ..add(utf8.encode('<html>502 Bad Gateway</html>'));
      });
      addTearDown(() => server.close(force: true));

      await expectLater(
        RestAnonymizer(baseUrl: _baseOf(server)).anonymize('x'),
        throwsA(isA<AnonymizerException>()
            .having((e) => e.message, 'message', contains('500'))),
      );
    });

    test('서버가 없으면 unavailable — 다른 백엔드로 넘길 수 있다', () async {
      // 포트를 열었다 바로 닫아 "아무도 듣지 않는 주소"를 만든다.
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final base = _baseOf(server);
      await server.close(force: true);

      await expectLater(
        RestAnonymizer(baseUrl: base).anonymize('x'),
        throwsA(isA<AnonymizerUnavailableException>()),
      );
    });

    test('지원하지 않는 옵션은 호출 전에 안내와 함께 거절한다', () async {
      // 서버를 띄우지 않아도 실패해야 한다 — 네트워크를 타기 전에 걸러야 하므로.
      await expectLater(
        RestAnonymizer(baseUrl: Uri.parse('http://127.0.0.1:1'))
            .anonymize('x', options: const AnonymizeOptions(useLlm: true)),
        throwsA(
          isA<AnonymizerException>()
              .having((e) => e.message, 'message', contains('이름 정밀 탐지'))
              // unavailable이면 다른 백엔드로 넘어가는데, 이건 그런 종류가 아니다.
              .having((e) => e is AnonymizerUnavailableException, 'unavailable', isFalse),
        ),
      );
    });
  });
}
