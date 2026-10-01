// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/models/sample_texts.dart';
import 'package:maskingtape_desktop/theme.dart';
import 'package:maskingtape_desktop/widgets/sample_tabs.dart';

/// 샘플 서랍(#587) — 웹 SampleTabs와 같은 동작: 탭은 미리보기만 바꾸고, 「입력창에 넣기」가 콜백을 부른다.
Widget _host(ValueChanged<String> onPick) => MaterialApp(
      theme: AppTheme.light(),
      home: Scaffold(
        body: SizedBox(width: 600, height: 500, child: SampleTabs(onPick: onPick)),
      ),
    );

void main() {
  test('샘플은 웹 presets.ts와 같은 9개이고, 종류 태그는 전부 라벨이 있다', () {
    expect(SampleText.all, hasLength(9));
    for (final sample in SampleText.all) {
      expect(sample.kinds, isNotEmpty, reason: sample.label);
      for (final kind in sample.kinds) {
        expect(
          Detection.labelOf(kind),
          isNot(startsWith('기타')),
          reason: '$kind in ${sample.label}',
        );
      }
    }
  });

  testWidgets('처음엔 첫 샘플이 선택돼 종류 태그와 미리보기가 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(_host((_) {}));

    final first = SampleText.all.first;
    expect(find.text(first.label), findsOneWidget);
    expect(find.text(first.text), findsOneWidget);
    for (final kind in first.kinds) {
      expect(find.text(Detection.labelOf(kind)), findsOneWidget);
    }
  });

  testWidgets('탭을 바꾸면 미리보기가 바뀌고, 「입력창에 넣기」를 눌러야 콜백이 불린다', (
    WidgetTester tester,
  ) async {
    String? picked;
    await tester.pumpWidget(_host((text) => picked = text));

    final rental = SampleText.all.last;
    await tester.ensureVisible(find.text(rental.label));
    await tester.tap(find.text(rental.label));
    await tester.pump();

    expect(find.text(rental.text), findsOneWidget);
    expect(find.text(SampleText.all.first.text), findsNothing);
    expect(find.text('운전면허'), findsOneWidget);
    expect(picked, isNull);

    await tester.tap(find.text('입력창에 넣기'));
    await tester.pump();
    expect(picked, rental.text);
  });
}
