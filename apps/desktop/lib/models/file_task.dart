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

  String get name => path.split(RegExp(r'[\\/]')).last;
}
