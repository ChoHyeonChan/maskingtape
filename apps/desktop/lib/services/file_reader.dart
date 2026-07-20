import 'dart:convert';
import 'dart:io';

import 'package:cp949_codec/cp949_codec.dart';

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
class FileReader {
  const FileReader({this.maxBytes = defaultMaxBytes});

  static const defaultMaxBytes = 10 * 1024 * 1024;
  static const supportedExtensions = {'txt', 'csv', 'tsv', 'md', 'json', 'log'};

  final int maxBytes;

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
            : '지원하지 않는 형식(.$ext)입니다 — 텍스트 파일(txt·csv·md 등)만 처리합니다',
      );
    }

    final file = File(path);
    final length = await file.length();
    if (length == 0) {
      throw const FileReadException('빈 파일입니다');
    }
    if (length > maxBytes) {
      final sizeMb = (length / (1024 * 1024)).toStringAsFixed(1);
      throw FileReadException(
        '파일이 너무 큽니다 (${sizeMb}MB — 최대 ${maxBytes ~/ (1024 * 1024)}MB)',
      );
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
