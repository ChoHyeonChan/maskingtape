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
  static String maskedPathFor(String path) {
    final sep = path.lastIndexOf(RegExp(r'[\\/]'));
    final dot = path.lastIndexOf('.');
    if (dot <= sep) {
      return '${path}_masked';
    }
    return '${path.substring(0, dot)}_masked${path.substring(dot)}';
  }

  /// isCancelled가 true를 돌려주면 다음 파일부터 처리하지 않는다
  /// (진행 중이던 파일은 마저 끝내고, 남은 파일은 대기 상태로 남는다).
  Future<void> processAll(
    List<FileTask> tasks,
    void Function() onUpdate, {
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
        final result = await anonymizer.anonymize(text);
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
      }
      onUpdate();
    }
  }
}
