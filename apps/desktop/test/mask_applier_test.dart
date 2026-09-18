import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/mask_applier.dart';

// 합성 문장 — 실제 개인정보 없음.
const _text = '연락처 010-1234-5678, 주민등록번호 800101-1234560, 메일 hong@example.com 끝';

Detection _d(String kind, String value) => Detection(
  kind: kind,
  start: _text.indexOf(value),
  end: _text.indexOf(value) + value.length,
  text: value,
);

final _phone = _d('phone', '010-1234-5678');
final _rrn = _d('rrn', '800101-1234560');
final _email = _d('email', 'hong@example.com');

void main() {
  group('MaskApplier', () {
    test('mask — 전부 가리면 코어 CLI 출력과 같다 (같은 길이의 *)', () {
      final out = MaskApplier.apply(
        _text,
        [_phone, _rrn, _email],
        strategy: MaskStrategy.mask,
        isMasked: (_) => true,
      );
      // 코어 `maskingtape --strategy mask`를 같은 문장으로 돌린 실측값.
      expect(
        out,
        '연락처 *************, 주민등록번호 **************, 메일 **************** 끝',
      );
    });

    test('label — 전부 가리면 코어 CLI 출력과 같다 (코어 라벨 어휘)', () {
      final out = MaskApplier.apply(
        _text,
        [_phone, _rrn, _email],
        strategy: MaskStrategy.label,
        isMasked: (_) => true,
      );
      expect(out, '연락처 [전화번호], 주민등록번호 [주민등록번호], 메일 [이메일] 끝');
    });

    test('노출로 고른 항목은 원문 그대로 남고 나머지만 가려진다', () {
      final out = MaskApplier.apply(
        _text,
        [_phone, _rrn, _email],
        strategy: MaskStrategy.mask,
        isMasked: (d) => d != _rrn,
      );
      expect(
        out,
        '연락처 *************, 주민등록번호 800101-1234560, 메일 **************** 끝',
      );
    });

    test('모르는 kind의 라벨은 [kind]로 떨어져 눈에 띈다', () {
      final out = MaskApplier.apply(
        'x 1234 y',
        [Detection(kind: 'new_kind', start: 2, end: 6, text: '1234')],
        strategy: MaskStrategy.label,
        isMasked: (_) => true,
      );
      expect(out, 'x [new_kind] y');
    });

    test('겹치는 구간은 앞의 것만 치환하고 뒤는 건너뛴다', () {
      final out = MaskApplier.apply(
        'ab12345cd',
        [
          Detection(kind: 'phone', start: 2, end: 7, text: '12345'),
          Detection(kind: 'card', start: 4, end: 9, text: '345cd'),
        ],
        strategy: MaskStrategy.mask,
        isMasked: (_) => true,
      );
      expect(out, 'ab*****cd');
    });

    test('탐지 순서가 뒤섞여 와도 원문 위치 순으로 치환한다', () {
      final out = MaskApplier.apply(
        _text,
        [_email, _rrn, _phone],
        strategy: MaskStrategy.mask,
        isMasked: (_) => true,
      );
      expect(
        out,
        '연락처 *************, 주민등록번호 **************, 메일 **************** 끝',
      );
    });

    test('pseudonym은 지원하지 않는다 — 코어가 준 결과를 써야 한다', () {
      expect(MaskApplier.supports(MaskStrategy.pseudonym), isFalse);
      expect(MaskApplier.supports(MaskStrategy.mask), isTrue);
      expect(MaskApplier.supports(MaskStrategy.label), isTrue);
    });
  });
}
