import 'detection.dart';

enum FileTaskStatus { waiting, processing, done, failed }

/// 드롭된 파일 하나의 처리 상태와 결과.
class FileTask {
  FileTask(this.path);

  final String path;
  FileTaskStatus status = FileTaskStatus.waiting;
  List<Detection> detections = const [];
  String? outputPath;
  String? error;

  /// 결과 미리보기용 — 완료된 작업만 값을 가진다.
  String? originalText;
  String? maskedText;

  String get name => path.split(RegExp(r'[\\/]')).last;
}
