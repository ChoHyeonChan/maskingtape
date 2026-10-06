// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/file_reader.dart';
import 'package:maskingtape_desktop/services/pdf_text_extractor.dart';

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

  group('PDF', () {
    // PDF 바이트는 진짜일 필요가 없다 — 추출은 가짜 추출기가 한다(실제 pypdf 추출은
    // installer/build.py의 확인 실행과 수동 확인으로 본다).
    Future<File> pdfFile(String name) async {
      final f = newFile(name);
      await f.writeAsString('%PDF-1.4 합성');
      return f;
    }

    test('추출기가 뽑은 글자를 그대로 돌려준다', () async {
      final f = await pdfFile('상담.PDF');
      final reader = FileReader(
        pdfExtractor: _FakePdf(text: '고객 김민수님 010-1234-5678'),
      );

      expect(await reader.read(f.path), '고객 김민수님 010-1234-5678');
    });

    test('추출 실패 안내는 FileReadException으로 옮긴다', () async {
      final f = await pdfFile('잠금.pdf');
      final reader = FileReader(
        pdfExtractor: _FakePdf(error: '암호가 걸린 PDF는 처리하지 않습니다'),
      );

      expect(
        () => reader.read(f.path),
        throwsA(
          isA<FileReadException>().having(
            (e) => e.message,
            'message',
            '암호가 걸린 PDF는 처리하지 않습니다',
          ),
        ),
      );
    });

    test('글자가 없는 PDF(스캔본)는 실패로 알린다', () async {
      final f = await pdfFile('스캔.pdf');
      final reader = FileReader(pdfExtractor: _FakePdf(text: ' \n\n '));

      expect(
        () => reader.read(f.path),
        throwsA(
          isA<FileReadException>().having(
            (e) => e.message,
            'message',
            startsWith('PDF에서 글자를 찾지 못했습니다'),
          ),
        ),
      );
    });

    test('PDF는 텍스트와 다른 크기 상한을 쓴다', () async {
      final f = await pdfFile('보고서.pdf');

      // 텍스트 상한보다 커도 PDF 상한 안이면 읽는다.
      final roomy = FileReader(maxBytes: 4, pdfExtractor: _FakePdf(text: '내용'));
      expect(await roomy.read(f.path), '내용');

      final tight = FileReader(
        maxPdfBytes: 4,
        pdfExtractor: _FakePdf(text: '내용'),
      );
      expect(() => tight.read(f.path), throwsA(isA<FileReadException>()));
    });

    test('PDF 결과 파일(_pdf_masked.txt)은 재처리를 거부한다', () async {
      final f = newFile('상담_pdf_masked.txt');
      await f.writeAsString('고객 ***님');

      expect(
        () => const FileReader().read(f.path),
        throwsA(isA<FileReadException>()),
      );
    });
  });
}

class _FakePdf implements PdfTextExtractor {
  _FakePdf({this.text, this.error});

  final String? text;
  final String? error;

  @override
  Future<String> extract(String path) async {
    if (error != null) {
      throw PdfTextException(error!);
    }
    return text!;
  }

  @override
  String? get python => null;

  @override
  Duration get timeout => Duration.zero;
}
