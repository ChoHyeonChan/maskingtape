import 'dart:convert';
import 'dart:io';

/// 이름 정밀 탐지에 쓰는 로컬 LLM의 준비 상태.
///
/// "켰는데 왜 안 되지"를 실패한 뒤에야 알게 되는 걸 막으려고, 처리를 돌리기 전에
/// 미리 확인해서 보여준다. 상태를 넷으로 나눈 이유는 **사용자가 할 일이 각각 다르기**
/// 때문이다 — Ollama를 켤지, 모델을 받을지, 그냥 기다리면 되는지.
enum LlmReadiness {
  /// 아직 확인 중.
  checking,

  /// Ollama에 연결하지 못했다 — 실행돼 있지 않거나 다른 포트를 쓴다.
  offline,

  /// Ollama는 떠 있는데 쓸 모델이 없다 — `ollama pull`이 필요하다.
  modelMissing,

  /// 모델은 받아뒀지만 메모리에 올라가 있지 않다 — 첫 호출에서 로딩 시간이 걸린다.
  downloaded,

  /// 모델이 메모리에 로드돼 있다 — 바로 응답한다.
  loaded,
}

/// 확인 결과 — 상태와 사용자에게 보여줄 안내를 함께 들고 다닌다.
class LlmStatus {
  const LlmStatus(this.readiness, {this.detail = ''});

  const LlmStatus.checking() : this(LlmReadiness.checking);

  final LlmReadiness readiness;

  /// 상태를 보완하는 짧은 설명(모델명, 확인해야 할 것 등).
  final String detail;

  /// 이름 정밀 탐지를 지금 켜도 되는지.
  bool get usable =>
      readiness == LlmReadiness.loaded || readiness == LlmReadiness.downloaded;

  /// 툴바 칩에 쓸 짧은 문구.
  String get label => switch (readiness) {
        LlmReadiness.checking => 'LLM 확인 중…',
        LlmReadiness.offline => 'Ollama 미실행',
        LlmReadiness.modelMissing => '모델 없음',
        LlmReadiness.downloaded => 'LLM 준비됨',
        LlmReadiness.loaded => 'LLM 로드됨',
      };
}

/// 로컬 Ollama에 상태만 물어보는 프로브.
///
/// 탐지·비식별화는 여기서 하지 않는다 — 그건 core CLI와 apps/api의 몫이다(§3).
/// 이 파일이 하는 일은 "쓸 수 있는 상태인가"를 읽는 것뿐이라 원문 텍스트를 보내지 않는다.
class OllamaProbe {
  OllamaProbe({
    Uri? host,
    this.model = defaultModel,
    HttpClient? client,
    this.timeout = const Duration(seconds: 2),
  })  : host = host ?? Uri.parse(defaultHost),
        _client = client ?? HttpClient();

  /// core의 name_llm.py DEFAULT_HOST와 같은 주소.
  static const defaultHost = 'http://127.0.0.1:11434';

  /// core의 name_llm.py DEFAULT_MODEL과 **같은 값을 유지해야 한다**.
  /// 코어가 기본 모델을 바꾸면 여기도 따라와야 한다 — 자동 동기화 수단이 없다(#187과 같은 종류의 문제).
  static const defaultModel = 'qwen2.5:7b';

  final Uri host;
  final String model;
  final Duration timeout;
  final HttpClient _client;

  /// 상태를 한 번 확인한다. 네트워크 문제는 예외 대신 [LlmStatus]로 돌려준다 —
  /// 이건 "확인"이지 "실패해도 되는 처리"가 아니라, 호출부가 try/catch를 두르지 않게 한다.
  Future<LlmStatus> check() async {
    final List<String> installed;
    try {
      installed = _modelNames(await _get('/api/tags'));
    } catch (_) {
      return LlmStatus(
        LlmReadiness.offline,
        detail: 'Ollama에 연결하지 못했습니다 ($host)',
      );
    }

    if (!_hasModel(installed)) {
      return LlmStatus(
        LlmReadiness.modelMissing,
        detail: '`ollama pull $model` 로 모델을 먼저 받으세요',
      );
    }

    // /api/ps는 **지금 메모리에 올라가 있는** 모델만 준다. 여기까지 왔으면 모델은 있으므로,
    // 이 호출이 실패해도 "받아는 뒀다"로 본다 — 로드 여부는 부가 정보지 차단 요인이 아니다.
    try {
      if (_hasModel(_modelNames(await _get('/api/ps')))) {
        return LlmStatus(LlmReadiness.loaded, detail: model);
      }
    } catch (_) {
      // 무시하고 downloaded로 떨어진다.
    }
    return LlmStatus(
      LlmReadiness.downloaded,
      detail: '$model · 첫 호출에서 모델 로딩 시간이 걸립니다',
    );
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final request = await _client.getUrl(host.resolve(path)).timeout(timeout);
    final response = await request.close().timeout(timeout);
    final raw = await response.transform(utf8.decoder).join().timeout(timeout);
    if (response.statusCode != HttpStatus.ok) {
      throw HttpException('${response.statusCode}', uri: host.resolve(path));
    }
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  static List<String> _modelNames(Map<String, dynamic> body) => [
        for (final m in (body['models'] as List<dynamic>? ?? []))
          if (m is Map<String, dynamic> && m['name'] is String) m['name'] as String,
      ];

  /// Ollama는 태그를 붙여 돌려주기도 한다("qwen2.5:7b" ↔ "qwen2.5:7b-instruct-q4").
  /// 태그까지 정확히 맞추라고 하면 멀쩡히 받아둔 모델을 "없음"으로 오인하므로 접두어로 본다.
  bool _hasModel(List<String> installed) =>
      installed.any((name) => name == model || name.startsWith('$model-'));
}
