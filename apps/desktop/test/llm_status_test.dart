import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/llm_status.dart';

/// Ollama 흉내 서버 — /api/tags(받아둔 모델)와 /api/ps(메모리에 올라간 모델)만 답한다.
Future<HttpServer> _fakeOllama({
  required List<String> installed,
  List<String> loaded = const [],
  int status = HttpStatus.ok,
}) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    final names = request.uri.path == '/api/ps' ? loaded : installed;
    request.response
      ..statusCode = status
      ..add(utf8.encode(jsonEncode({
        'models': [
          for (final name in names) {'name': name},
        ],
      })));
    await request.response.close();
  });
  return server;
}

Uri _uriOf(HttpServer server) =>
    Uri.parse('http://${server.address.address}:${server.port}');

void main() {
  test('Ollama가 안 떠 있으면 offline', () async {
    // 포트를 열었다 바로 닫아 "아무도 듣지 않는 주소"를 만든다.
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final host = _uriOf(server);
    await server.close(force: true);

    final status = await OllamaProbe(host: host).check();

    expect(status.readiness, LlmReadiness.offline);
    expect(status.usable, isFalse);
    expect(status.label, 'Ollama 미실행');
  });

  test('모델이 없으면 modelMissing — pull 명령을 안내한다', () async {
    final server = await _fakeOllama(installed: ['llama3:8b']);
    addTearDown(() => server.close(force: true));

    final status = await OllamaProbe(host: _uriOf(server)).check();

    expect(status.readiness, LlmReadiness.modelMissing);
    expect(status.usable, isFalse);
    expect(status.detail, contains('ollama pull qwen2.5:7b'));
  });

  test('받아만 뒀으면 downloaded — 쓸 수는 있다', () async {
    final server = await _fakeOllama(installed: ['qwen2.5:7b'], loaded: []);
    addTearDown(() => server.close(force: true));

    final status = await OllamaProbe(host: _uriOf(server)).check();

    expect(status.readiness, LlmReadiness.downloaded);
    expect(status.usable, isTrue, reason: '로딩이 걸릴 뿐 동작은 한다');
    expect(status.detail, contains('로딩'));
  });

  test('메모리에 올라가 있으면 loaded', () async {
    final server = await _fakeOllama(
      installed: ['qwen2.5:7b'],
      loaded: ['qwen2.5:7b'],
    );
    addTearDown(() => server.close(force: true));

    final status = await OllamaProbe(host: _uriOf(server)).check();

    expect(status.readiness, LlmReadiness.loaded);
    expect(status.usable, isTrue);
    expect(status.label, 'LLM 로드됨');
  });

  test('태그가 붙은 변형 모델명도 같은 모델로 본다', () async {
    // 멀쩡히 받아둔 모델을 "없음"으로 오인하면 안 된다.
    final server = await _fakeOllama(installed: ['qwen2.5:7b-instruct-q4_K_M']);
    addTearDown(() => server.close(force: true));

    final status = await OllamaProbe(host: _uriOf(server)).check();

    expect(status.readiness, LlmReadiness.downloaded);
  });

  test('/api/tags가 오류를 주면 offline으로 본다', () async {
    final server = await _fakeOllama(
      installed: const [],
      status: HttpStatus.internalServerError,
    );
    addTearDown(() => server.close(force: true));

    final status = await OllamaProbe(host: _uriOf(server)).check();

    expect(status.readiness, LlmReadiness.offline);
  });
}
