import 'package:file_selector/file_selector.dart';

import 'file_reader.dart';

/// OS 파일 선택 대화상자를 열어 지원 확장자의 파일 경로들을 돌려준다.
/// 취소하면 빈 목록.
Future<List<String>> pickTextFiles() async {
  final group = XTypeGroup(
    label: '텍스트 문서',
    extensions: FileReader.supportedExtensions.toList(),
  );
  final files = await openFiles(acceptedTypeGroups: [group]);
  return [for (final f in files) f.path];
}
