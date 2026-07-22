import 'dart:io';

/// 탐색기에서 해당 파일이 선택된 상태로 폴더를 연다 (Windows 전용 앱).
Future<void> revealInExplorer(String path) async {
  await Process.start('explorer.exe', ['/select,$path']);
}
