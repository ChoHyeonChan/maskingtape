import 'dart:convert';
import 'dart:io';

import '../models/file_task.dart';
import 'anonymizer.dart';

/// 파일 목록을 순차 처리한다: 읽기 → 비식별화 → `_masked` 사본 저장.
/// UI는 onUpdate 콜백으로 상태 변화를 전달받아 다시 그리기만 한다.
class BatchProcessor {
  const BatchProcessor(this.anonymizer);

  final Anonymizer anonymizer;

  /// `이름.확장자` → `이름_masked.확장자` (확장자 없으면 끝에 `_masked`).
  static String maskedPathFor(String path) {
    final sep = path.lastIndexOf(RegExp(r'[\\/]'));
    final dot = path.lastIndexOf('.');
    if (dot <= sep) {
      return '${path}_masked';
    }
    return '${path.substring(0, dot)}_masked${path.substring(dot)}';
  }

  Future<void> processAll(
    List<FileTask> tasks,
    void Function() onUpdate,
  ) async {
    for (final task in tasks) {
      if (task.status != FileTaskStatus.waiting) {
        continue;
      }
      task.status = FileTaskStatus.processing;
      onUpdate();
      try {
        final bytes = await File(task.path).readAsBytes();
        var text = utf8.decode(bytes);
        // 메모장·PowerShell이 붙이는 UTF-8 BOM(U+FEFF)은 탐지 위치를 밀기 때문에 뗀다.
        if (text.isNotEmpty && text.codeUnitAt(0) == 0xFEFF) {
          text = text.substring(1);
        }
        final result = await anonymizer.anonymize(text);
        final outputPath = maskedPathFor(task.path);
        await File(outputPath).writeAsString(result.maskedText);
        task
          ..detections = result.detections
          ..outputPath = outputPath
          ..status = FileTaskStatus.done;
      } on FormatException {
        task
          ..error = 'UTF-8 텍스트 파일이 아닙니다'
          ..status = FileTaskStatus.failed;
      } on AnonymizerException catch (e) {
        task
          ..error = e.message
          ..status = FileTaskStatus.failed;
      } on FileSystemException catch (e) {
        task
          ..error = '파일 읽기/쓰기 실패: ${e.osError?.message ?? e.message}'
          ..status = FileTaskStatus.failed;
      }
      onUpdate();
    }
  }
}
