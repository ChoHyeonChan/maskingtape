// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:convert';
import 'dart:io';

import '../models/detection.dart';
import 'anonymizer.dart';
import 'code_point_offsets.dart';

/// core CLI(`maskingtape`)를 서브프로세스로 호출하는 구현.
/// 탐지 로직은 전부 core에 있고, 여기는 stdin으로 텍스트를 넘기고 stdout을 읽기만 한다.
class CliAnonymizer implements Anonymizer {
  const CliAnonymizer({
    this.command = 'maskingtape',
    this.leadingArgs = const [],
  });

  /// 실행할 CLI — 설치판이 동봉한 Python의 전체 경로이거나, PATH에서 찾는 `maskingtape`
  /// (`cli_locator.dart`가 정한다).
  final String command;

  /// 사용자 인자 앞에 붙는 고정 인자 — 동봉 Python으로 부를 때의 `-X utf8 -m maskingtape.cli`.
  final List<String> leadingArgs;

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
    // core 위치는 코드포인트 기준이라 Dart(UTF-16) 기준으로 바꿔 둔다(#496).
    final detections = CodePointOffsets(text).convert(
      (jsonDecode(scanOut) as List<dynamic>)
          .map((e) => Detection.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
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
        [...leadingArgs, ...args],
        // 파이썬이 콘솔 코드페이지(cp949) 대신 UTF-8로 파이프를 읽고 쓰게 한다.
        environment: {'PYTHONUTF8': '1'},
      );
    } on ProcessException {
      // CLI 자체가 없는 것이므로 다른 백엔드로 넘길 수 있다 (FallbackAnonymizer 참고).
      throw const AnonymizerUnavailableException(
        'maskingtape CLI를 찾을 수 없습니다 — 설치판이면 다시 설치하고, '
        '소스로 실행 중이면 packages/core 설치와 PATH를 확인하세요',
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
