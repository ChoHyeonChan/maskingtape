// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/code_point_offsets.dart';
import 'package:maskingtape_desktop/services/mask_applier.dart';

// 합성 주민번호(체크섬만 맞춘 가짜 값) — 실제 개인정보 없음.
const _rrn = '800101-1234560';

/// core가 주는 것과 같은 **코드포인트** 위치의 탐지 — 파이썬 `str.index`와 같은 기준.
Detection _coreDetection(String text, String value) {
  final cps = text.runes.toList();
  final target = value.runes.toList();
  for (var i = 0; i + target.length <= cps.length; i++) {
    var hit = true;
    for (var j = 0; j < target.length; j++) {
      if (cps[i + j] != target[j]) {
        hit = false;
        break;
      }
    }
    if (hit) {
      return Detection(
        kind: 'rrn',
        start: i,
        end: i + target.length,
        text: value,
      );
    }
  }
  throw StateError('not found');
}

String _emojis(int k) => '😀' * k;

void main() {
  group('CodePointOffsets', () {
    test('BMP 글자만 있으면 위치가 그대로다 (한글·숫자)', () {
      const text = '신청자 주민번호 $_rrn 확인';
      final d = _coreDetection(text, _rrn);
      final converted = CodePointOffsets(text).convert([d]).single;
      expect(converted.start, d.start);
      expect(converted.end, d.end);
      expect(text.substring(converted.start, converted.end), _rrn);
    });

    // #496 재현값: 이모지 1·3·14개. core 위치를 그대로 쓰면 끝 1·3자, 14개면 전체가 남았다.
    for (final k in [1, 3, 14]) {
      test('이모지 $k개 뒤의 주민번호를 정확히 가리킨다', () {
        final text = '${_emojis(k)} 주민 $_rrn';
        final d = _coreDetection(text, _rrn);
        // 바꾸기 전: core 위치로 Dart에서 자르면 주민번호와 다르다(버그 조건 확인).
        expect(text.substring(d.start, d.end), isNot(_rrn));

        final converted = CodePointOffsets(text).convert([d]).single;
        expect(text.substring(converted.start, converted.end), _rrn);
      });
    }

    test('구간 안에 이모지가 있어도 양 끝이 맞는다', () {
      const value = '김😀민';
      const text = '고객 $value님';
      final d = _coreDetection(text, value);
      final converted = CodePointOffsets(text).convert([d]).single;
      expect(text.substring(converted.start, converted.end), value);
    });

    test('범위를 벗어난 위치는 조용히 넘기지 않고 실패로 알린다', () {
      final offsets = CodePointOffsets('짧은 글');
      expect(
        () => offsets.convert([
          const Detection(kind: 'rrn', start: 0, end: 99, text: 'x'),
        ]),
        throwsA(isA<AnonymizerException>()),
      );
    });

    test('빈 문자열도 다룬다', () {
      final offsets = CodePointOffsets('');
      expect(offsets.codePointLength, 0);
      expect(offsets.toUtf16(0), 0);
    });
  });

  group('MaskApplier + 변환 — 결과에 원문 숫자가 남지 않는다', () {
    for (final k in [1, 3, 14]) {
      test('이모지 $k개', () {
        final text = '${_emojis(k)} 주민 $_rrn';
        final detections = CodePointOffsets(
          text,
        ).convert([_coreDetection(text, _rrn)]);
        final out = MaskApplier.apply(
          text,
          detections,
          strategy: MaskStrategy.mask,
          isMasked: (_) => true,
        );
        // core `--strategy mask`와 같은 결과여야 한다.
        expect(out, '${_emojis(k)} 주민 ${'*' * _rrn.length}');
        for (final digit in '0123456789'.split('')) {
          expect(
            out.contains(digit),
            isFalse,
            reason: '원문 숫자 "$digit"가 남음: $out',
          );
        }
      });
    }

    test('별표 개수는 core처럼 글자(코드포인트) 수다', () {
      const value = '김😀민'; // 3글자, UTF-16 4칸
      const text = '고객 $value님';
      final detections = CodePointOffsets(
        text,
      ).convert([_coreDetection(text, value)]);
      final out = MaskApplier.apply(
        text,
        detections,
        strategy: MaskStrategy.mask,
        isMasked: (_) => true,
      );
      expect(out, '고객 ***님');
    });
  });
}
