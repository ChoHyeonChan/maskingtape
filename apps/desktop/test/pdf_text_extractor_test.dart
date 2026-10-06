// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/services/pdf_text_extractor.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('failureMessage', () {
    test('스크립트의 「오류: 」 줄만 안내로 옮긴다', () {
      const stderr =
          'Traceback (most recent call last):\n'
          '  File "C:\\Users\\합성\\문서.pdf"\n'
          '오류: 암호가 걸린 PDF는 처리하지 않습니다\n';
      expect(
        PdfTextExtractor.failureMessage(1, stderr),
        '암호가 걸린 PDF는 처리하지 않습니다',
      );
    });

    test('안내 줄이 없으면 표준오류를 옮기지 않고 종료 코드만 알린다', () {
      // 트레이스백에는 경로·내용 조각이 섞일 수 있다.
      expect(
        PdfTextExtractor.failureMessage(9009, 'Python was not found; 고객 김민수'),
        'PDF에서 글자를 뽑지 못했습니다 (코드 9009)',
      );
    });
  });

  test('Python을 실행하지 못하면 다시 설치하라고 안내한다', () async {
    const extractor = PdfTextExtractor(
      python: 'no-such-python-for-maskingtape-test',
    );

    expect(
      () => extractor.extract('합성.pdf'),
      throwsA(
        isA<PdfTextException>().having(
          (e) => e.message,
          'message',
          startsWith('PDF를 읽을 Python을 찾지 못했습니다'),
        ),
      ),
    );
  });
}
