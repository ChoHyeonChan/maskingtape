// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:io';

import '../models/file_task.dart';
import 'anonymizer.dart';
import 'file_reader.dart';

/// 파일 목록을 순차 처리한다: 읽기 → 비식별화 → `_masked` 사본 저장.
/// UI는 onUpdate 콜백으로 상태 변화를 전달받아 다시 그리기만 한다.
class BatchProcessor {
  const BatchProcessor(this.anonymizer, {this.fileReader = const FileReader()});

  final Anonymizer anonymizer;
  final FileReader fileReader;

  /// `이름.확장자` → `이름_masked.확장자` (확장자 없으면 끝에 `_masked`).
  ///
  /// PDF는 뽑은 글자만 저장하므로 `이름_pdf_masked.txt`다. `이름_masked.txt`로 두면 같은 폴더의
  /// `이름.txt` 결과를 덮어쓴다.
  static String maskedPathFor(String path) {
    final sep = path.lastIndexOf(RegExp(r'[\\/]'));
    final dot = path.lastIndexOf('.');
    if (dot <= sep) {
      return '${path}_masked';
    }
    final stem = path.substring(0, dot);
    final ext = path.substring(dot);
    if (ext.toLowerCase() == '.pdf') {
      return '${stem}_pdf_masked.txt';
    }
    return '${stem}_masked$ext';
  }

  /// isCancelled가 true를 돌려주면 다음 파일부터 처리하지 않는다
  /// (진행 중이던 파일은 마저 끝내고, 남은 파일은 대기 상태로 남는다).
  Future<void> processAll(
    List<FileTask> tasks,
    void Function() onUpdate, {
    AnonymizeOptions options = const AnonymizeOptions(),
    bool Function()? isCancelled,
  }) async {
    for (final task in tasks) {
      if (isCancelled?.call() ?? false) {
        break;
      }
      if (task.status != FileTaskStatus.waiting) {
        continue;
      }
      task.status = FileTaskStatus.processing;
      onUpdate();
      try {
        final text = await fileReader.read(task.path);
        final result = await anonymizer.anonymize(text, options: options);
        final outputPath = maskedPathFor(task.path);
        await File(outputPath).writeAsString(result.maskedText);
        task
          ..detections = result.detections
          ..outputPath = outputPath
          ..status = FileTaskStatus.done;
      } on FileReadException catch (e) {
        task
          ..error = e.message
          ..status = FileTaskStatus.failed;
      } on AnonymizerException catch (e) {
        task
          ..error = e.message
          ..status = FileTaskStatus.failed;
      } on FileSystemException catch (e) {
        task
          ..error = '파일 읽기/쓰기 실패: ${e.osError?.message ?? e.message}'
          ..status = FileTaskStatus.failed;
      } catch (_) {
        // 예상 밖 오류(응답 형식이 달라진 경우 등)도 이 파일만 실패로 두고 다음 파일로 간다.
        // 예전엔 여기서 빠져나가 파일이 「처리 중」에 멈추고 앱 전체가 갇혔다(#497).
        // 예외 문자열은 화면에 넣지 않는다 — 형식 오류 메시지에 원문 조각이 담길 수 있다.
        task
          ..error = unexpectedErrorMessage
          ..status = FileTaskStatus.failed;
      }
      onUpdate();
    }
  }
}
