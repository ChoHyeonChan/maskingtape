import 'dart:convert';
import 'dart:io';

import '../models/detection.dart';
import 'anonymizer.dart';

/// core CLI(`maskingtape`)를 서브프로세스로 호출하는 구현.
/// 탐지 로직은 전부 core에 있고, 여기는 stdin으로 텍스트를 넘기고 stdout을 읽기만 한다.
class CliAnonymizer implements Anonymizer {
  const CliAnonymizer({this.command = 'maskingtape'});

  /// 실행할 CLI 명령 — PATH에서 찾는다.
  final String command;

  /// CLI 인자 조립 — 탐지(`--scan`)와 마스킹 호출이 같은 조건을 쓰도록 한 곳에서 만든다.
  /// 둘의 조건이 어긋나면 화면의 탐지 요약과 저장된 결과가 서로 다른 기준이 된다.
  static List<String> argsFor(AnonymizeOptions options, {required bool scan}) =>
      [
        if (scan) '--scan' else ...['--strategy', options.strategy.wireName],
        if (options.useLlm) '--llm',
      ];

  @override
  Future<AnonymizeResult> anonymize(
    String text, {
    AnonymizeOptions options = const AnonymizeOptions(),
  }) async {
    // CLI는 탐지 JSON과 마스킹 텍스트를 따로 내보내므로 두 번 호출한다.
    // (LLM 모드에서는 모델 호출도 두 번이라 그만큼 느리다 — core에 한 번에
    //  둘 다 주는 출력 모드가 생기면 한 번으로 줄일 수 있다.)
    final scanOut = await _run(argsFor(options, scan: true), text);
    final detections = (jsonDecode(scanOut) as List<dynamic>)
        .map((e) => Detection.fromJson(e as Map<String, dynamic>))
        .toList();
    final masked = await _run(argsFor(options, scan: false), text);
    return AnonymizeResult(
      // print()가 붙인 마지막 줄바꿈 하나만 떼어낸다.
      maskedText: masked.replaceFirst(RegExp(r'\r?\n$'), ''),
      detections: detections,
    );
  }

  Future<String> _run(List<String> args, String input) async {
    final Process process;
    try {
      process = await Process.start(
        command,
        args,
        // 파이썬이 콘솔 코드페이지(cp949) 대신 UTF-8로 파이프를 읽고 쓰게 한다.
        environment: {'PYTHONUTF8': '1'},
      );
    } on ProcessException {
      throw const AnonymizerException(
        'maskingtape CLI를 찾을 수 없습니다 — packages/core 설치와 PATH를 확인하세요',
      );
    }
    final stdoutFuture = process.stdout.transform(utf8.decoder).join();
    final stderrFuture = process.stderr.transform(utf8.decoder).join();
    process.stdin.add(utf8.encode(input));
    await process.stdin.close();
    final exitCode = await process.exitCode;
    if (exitCode != 0) {
      throw AnonymizerException(_failureMessage(exitCode, await stderrFuture));
    }
    return stdoutFuture;
  }

  /// core가 `오류: ...`로 사용자용 안내(예: Ollama 미실행)를 주면 그대로 보여준다.
  /// 앱이 임의 문구로 덮으면 무엇을 고쳐야 하는지가 사라진다.
  static String _failureMessage(int exitCode, String stderr) {
    final trimmed = stderr.trim();
    const prefix = '오류: ';
    if (trimmed.startsWith(prefix)) {
      return trimmed.substring(prefix.length);
    }
    return 'CLI가 비정상 종료했습니다 (코드 $exitCode): $trimmed';
  }
}
