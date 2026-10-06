// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'dart:convert';
import 'dart:io';

import 'package:cp949_codec/cp949_codec.dart';

import 'pdf_text_extractor.dart';

/// 파일 읽기 실패 — 사용자에게 그대로 보여줄 한국어 메시지를 담는다.
class FileReadException implements Exception {
  const FileReadException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 드롭된 파일을 검증하고 텍스트로 읽는다.
///
/// 검증: 지원 확장자, 크기 상한, 빈 파일, 이미 처리된(`_masked`) 파일, 바이너리 감지.
/// 디코딩: UTF-8 우선, 실패 시 CP949(EUC-KR) 폴백 — 구형 메모장·엑셀 CSV 대응.
/// PDF는 [PdfTextExtractor]로 글자만 뽑는다 — 그 뒤 처리는 텍스트 파일과 같다.
class FileReader {
  const FileReader({
    this.maxBytes = defaultMaxBytes,
    this.maxPdfBytes = defaultMaxPdfBytes,
    this.pdfExtractor = const PdfTextExtractor(),
  });

  static const defaultMaxBytes = 10 * 1024 * 1024;

  /// PDF는 그림·글꼴이 함께 들어 있어 같은 글자 양이라도 파일이 훨씬 크다.
  static const defaultMaxPdfBytes = 50 * 1024 * 1024;
  static const supportedExtensions = {
    'txt',
    'csv',
    'tsv',
    'md',
    'json',
    'log',
    'pdf',
  };

  final int maxBytes;
  final int maxPdfBytes;
  final PdfTextExtractor pdfExtractor;

  Future<String> read(String path) async {
    final name = path.split(RegExp(r'[\\/]')).last;
    final dot = name.lastIndexOf('.');
    final ext = dot < 0 ? '' : name.substring(dot + 1).toLowerCase();
    final stem = dot < 0 ? name : name.substring(0, dot);

    if (stem.endsWith('_masked')) {
      throw const FileReadException('이미 비식별화된 결과 파일입니다');
    }
    if (!supportedExtensions.contains(ext)) {
      throw FileReadException(
        ext.isEmpty
            ? '확장자가 없는 파일은 지원하지 않습니다'
            : '지원하지 않는 형식(.$ext)입니다 — 텍스트 파일(txt·csv·md 등)과 PDF만 처리합니다',
      );
    }

    final isPdf = ext == 'pdf';
    final limit = isPdf ? maxPdfBytes : maxBytes;
    final file = File(path);
    final length = await file.length();
    if (length == 0) {
      throw const FileReadException('빈 파일입니다');
    }
    if (length > limit) {
      final sizeMb = (length / (1024 * 1024)).toStringAsFixed(1);
      throw FileReadException(
        '파일이 너무 큽니다 (${sizeMb}MB — 최대 ${limit ~/ (1024 * 1024)}MB)',
      );
    }

    if (isPdf) {
      return _readPdf(path);
    }

    final bytes = await file.readAsBytes();
    // NUL 바이트가 있으면 텍스트가 아니다 — 확장자만 txt인 바이너리 방어.
    if (bytes.take(8192).contains(0)) {
      throw const FileReadException('텍스트 파일이 아닙니다 (바이너리 내용)');
    }

    var text = _decode(bytes);
    // 메모장·PowerShell이 붙이는 UTF-8 BOM(U+FEFF)은 탐지 위치를 밀기 때문에 뗀다.
    if (text.isNotEmpty && text.codeUnitAt(0) == 0xFEFF) {
      text = text.substring(1);
    }
    return text;
  }

  Future<String> _readPdf(String path) async {
    final String text;
    try {
      text = await pdfExtractor.extract(path);
    } on PdfTextException catch (e) {
      throw FileReadException(e.message);
    }
    // 글자 층이 없는 PDF(스캔본 등)는 뽑히는 글자가 없다. 빈 결과를 「완료」로 두면
    // 가릴 것이 없었던 것처럼 보이므로 실패로 알린다.
    if (text.trim().isEmpty) {
      throw const FileReadException(
        'PDF에서 글자를 찾지 못했습니다 — 스캔한 이미지로 된 PDF는 처리하지 않습니다',
      );
    }
    return text;
  }

  String _decode(List<int> bytes) {
    try {
      return utf8.decode(bytes);
    } on FormatException {
      try {
        return cp949.decode(bytes);
      } on Exception {
        throw const FileReadException(
          '텍스트 인코딩을 해석할 수 없습니다 (UTF-8·CP949 모두 아님)',
        );
      }
    }
  }
}
