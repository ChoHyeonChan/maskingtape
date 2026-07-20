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

  @override
  Future<AnonymizeResult> anonymize(String text) async {
    final scanOut = await _run(['--scan'], text);
    final detections = (jsonDecode(scanOut) as List<dynamic>)
        .map((e) => Detection.fromJson(e as Map<String, dynamic>))
        .toList();
    final masked = await _run([], text);
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
      final stderr = (await stderrFuture).trim();
      throw AnonymizerException('CLI가 비정상 종료했습니다 (코드 $exitCode): $stderr');
    }
    return stdoutFuture;
  }
}
