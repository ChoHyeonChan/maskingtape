import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/main.dart';
import 'package:maskingtape_desktop/screens/home_screen.dart';

void main() {
  testWidgets('홈 화면에 드롭존 안내 문구가 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(const MaskingtapeApp());

    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);
    expect(find.text('여러 문서를 한 번에 비식별화합니다'), findsOneWidget);
  });

  testWidgets('드롭된 파일이 파일명과 개수로 목록에 표시된다', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: HomeScreen(
          initialFiles: [
            r'C:\docs\상담기록.txt',
            r'C:\docs\고객명단.csv',
          ],
        ),
      ),
    );

    expect(find.text('대기 중인 파일 2개'), findsOneWidget);
    expect(find.text('상담기록.txt'), findsOneWidget);
    expect(find.text('고객명단.csv'), findsOneWidget);
    expect(find.text('목록 비우기'), findsOneWidget);
  });

  testWidgets('목록 비우기를 누르면 드롭존만 남는다', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: HomeScreen(initialFiles: [r'C:\docs\상담기록.txt']),
      ),
    );

    await tester.tap(find.text('목록 비우기'));
    await tester.pump();

    expect(find.text('상담기록.txt'), findsNothing);
    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);
  });
}
