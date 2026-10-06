// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart' show rootBundle;

import 'cli_locator.dart';

/// PDF 글자 추출 실패 — 사용자에게 그대로 보여줄 한국어 메시지를 담는다.
class PdfTextException implements Exception {
  const PdfTextException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// PDF에서 글자를 뽑는다 — Python으로 `assets/pdf_text.py`(pypdf)를 돌린다.
///
/// - Python은 [locatePython]이 정한다: 설치판은 동봉 Python, 개발 환경은 PATH의 `python`.
/// - 스크립트는 `python - <경로>`로 띄워 **표준입력으로** 넘긴다. `-c` 인자로 넘기면 여러 줄·따옴표가
///   Windows 명령줄 인용 규칙을 타서 깨질 수 있다. `-B`·`-X utf8`은 CLI 호출과 같은 이유다(`cli_locator.dart`).
/// - 글자만 뽑는다. 탐지는 하지 않는다 — 뽑은 글자는 텍스트 파일과 똑같이 core CLI로 간다.
/// - 실패 안내는 스크립트가 표준오류에 쓴 `오류: ...` 줄만 화면에 옮긴다. 그 밖의 표준오류
///   (트레이스백 등)에는 경로나 내용 조각이 섞일 수 있어 옮기지 않는다.
class PdfTextExtractor {
  const PdfTextExtractor({
    this.python,
    this.timeout = const Duration(seconds: 60),
  });

  /// 실행할 Python. null이면 [locatePython] — 테스트에서 주입한다.
  final String? python;

  /// 이 시간 안에 끝나지 않으면 프로세스를 끊는다 — 비정상적으로 꼬인 PDF에서 배치가 멈추지 않게.
  final Duration timeout;

  static const scriptAsset = 'assets/pdf_text.py';

  Future<String> extract(String path) async {
    final script = await rootBundle.loadString(scriptAsset);
    final Process process;
    try {
      process = await Process.start(
        python ?? locatePython(),
        ['-B', '-X', 'utf8', '-', path],
        environment: {'PYTHONUTF8': '1'},
      );
    } on ProcessException {
      throw const PdfTextException('PDF를 읽을 Python을 찾지 못했습니다 — 설치판이면 다시 설치하세요');
    }
    final stdoutFuture = process.stdout.transform(utf8.decoder).join();
    final stderrFuture = process.stderr.transform(utf8.decoder).join();
    try {
      process.stdin.add(utf8.encode(script));
      await process.stdin.close();
    } on Object {
      // 스크립트를 다 읽기 전에 프로세스가 끝났다(PATH의 python이 MS Store 바로가기 등) — 아래 종료 코드로 판단한다.
    }

    final int exitCode;
    try {
      exitCode = await process.exitCode.timeout(timeout);
    } on TimeoutException {
      process.kill();
      throw PdfTextException('PDF 글자 추출이 ${timeout.inSeconds}초 안에 끝나지 않았습니다');
    }
    if (exitCode != 0) {
      throw PdfTextException(failureMessage(exitCode, await stderrFuture));
    }
    return stdoutFuture;
  }

  /// 스크립트의 `오류: ...` 줄이 있으면 그 안내를, 없으면 종료 코드만 담은 문구를 돌려준다.
  static String failureMessage(int exitCode, String stderr) {
    const prefix = '오류: ';
    for (final line in const LineSplitter().convert(stderr).reversed) {
      if (line.startsWith(prefix)) {
        return line.substring(prefix.length).trim();
      }
    }
    return 'PDF에서 글자를 뽑지 못했습니다 (코드 $exitCode)';
  }
}
