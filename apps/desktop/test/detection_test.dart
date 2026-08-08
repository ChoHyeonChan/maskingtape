import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/models/detection.dart';

Detection _d(String kind) =>
    Detection(kind: kind, start: 0, end: 1, text: 'x');

void main() {
  group('kindLabel', () {
    test('알려진 kind는 한국어 라벨로 바꾼다', () {
      expect(_d('rrn').kindLabel, '주민번호');
      expect(_d('phone').kindLabel, '전화번호');
      expect(_d('email').kindLabel, '이메일');
      expect(_d('name').kindLabel, '이름');
      expect(_d('address').kindLabel, '주소');
      // 코어에 추가된 신용카드 탐지기 (#61/#62) 대응
      expect(_d('card').kindLabel, '카드번호');
      // 코어에 추가된 사업자등록번호 탐지기 (#120) 대응
      expect(_d('biz_reg').kindLabel, '사업자등록번호');
      // 코어에 추가된 여권번호 탐지기 (#129) 대응
      expect(_d('passport').kindLabel, '여권번호');
      // 코어에 추가된 계좌번호 탐지기 (#180) 대응
      expect(_d('account').kindLabel, '계좌번호');
    });

    test('라벨 맵에 없는 kind는 kind(?)로 표시해 누락을 드러낸다', () {
      // 코어가 새 탐지기를 추가했는데 앱 라벨을 안 넣은 상황을 흉내 낸다.
      // 실재할 수 있는 이름(passport 등)을 쓰면 코어가 그 탐지기를 실제로 추가하는
      // 순간 "미지의 kind"라는 전제가 거짓이 되므로, 절대 kind가 될 수 없는 값을 쓴다.
      final unknown = _d('not_a_real_kind');
      expect(unknown.hasLabel, isFalse);
      expect(unknown.kindLabel, 'not_a_real_kind(?)');
    });
  });

  group('summarize', () {
    test('빈 목록은 "탐지 없음"', () {
      expect(Detection.summarize([]), '탐지 없음');
    });

    test('종류별 개수를 한국어 라벨로 합산한다', () {
      final detections = [
        _d('rrn'),
        _d('card'),
        _d('card'),
        _d('phone'),
      ];
      expect(Detection.summarize(detections), '주민번호 1 · 카드번호 2 · 전화번호 1');
    });
  });
}
