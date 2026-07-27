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

  // 원문·마스킹 텍스트는 여기 보관하지 않는다 — 대량 파일에서 메모리를 잡아먹는다.
  // 미리보기는 열 때 디스크에서 읽는다(원본 파일 + outputPath). 여기엔 작은
  // 메타데이터(탐지 목록·저장 경로·상태)만 남긴다.

  String get name => path.split(RegExp(r'[\\/]')).last;
}
