import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/file_reader.dart';

void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('file_reader_test');
  });

  tearDown(() => dir.delete(recursive: true));

  File newFile(String name) =>
      File('${dir.path}${Platform.pathSeparator}$name');

  test('UTF-8 파일을 읽고 BOM은 제거한다', () async {
    final f = newFile('a.txt');
    await f.writeAsBytes([0xEF, 0xBB, 0xBF, ...utf8.encode('안녕 010-1234-5678')]);

    final text = await const FileReader().read(f.path);

    expect(text, '안녕 010-1234-5678');
  });

  test('CP949 파일은 폴백 디코딩으로 읽는다', () async {
    final f = newFile('legacy.txt');
    // "아름다운"의 CP949 바이트 — 구형 메모장 저장 파일을 흉내 낸다.
    await f.writeAsBytes([0xBE, 0xC6, 0xB8, 0xA7, 0xB4, 0xD9, 0xBF, 0xEE]);

    final text = await const FileReader().read(f.path);

    expect(text, '아름다운');
  });

  test('_masked 결과 파일은 재처리를 거부한다', () async {
    final f = newFile('상담기록_masked.txt');
    await f.writeAsString('내용');

    expect(
      () => const FileReader().read(f.path),
      throwsA(isA<FileReadException>()),
    );
  });

  test('지원하지 않는 확장자는 거부한다', () async {
    final f = newFile('문서.hwp');
    await f.writeAsString('내용');

    expect(
      () => const FileReader().read(f.path),
      throwsA(isA<FileReadException>()),
    );
  });

  test('빈 파일은 거부한다', () async {
    final f = newFile('빈파일.txt');
    await f.writeAsBytes([]);

    expect(
      () => const FileReader().read(f.path),
      throwsA(isA<FileReadException>()),
    );
  });

  test('NUL 바이트가 있는 바이너리는 거부한다', () async {
    final f = newFile('가짜텍스트.txt');
    await f.writeAsBytes([0x61, 0x00, 0x62, 0x63]);

    expect(
      () => const FileReader().read(f.path),
      throwsA(isA<FileReadException>()),
    );
  });

  test('크기 상한을 넘는 파일은 거부한다', () async {
    final f = newFile('큰파일.txt');
    await f.writeAsString('가나다라마바사아자차');

    expect(
      () => const FileReader(maxBytes: 10).read(f.path),
      throwsA(isA<FileReadException>()),
    );
  });
}
