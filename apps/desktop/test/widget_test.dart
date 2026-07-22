import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/main.dart';
import 'package:maskingtape_desktop/screens/home_screen.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';

import 'fakes.dart';

void main() {
  testWidgets('홈 화면에 드롭존 안내 문구가 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(const MaskingtapeApp());

    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);
    expect(find.text('여러 문서를 한 번에 비식별화합니다'), findsOneWidget);
  });

  testWidgets('드롭된 파일이 파일명·개수·시작 버튼과 함께 표시된다',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          initialFiles: const [
            r'C:\docs\상담기록.txt',
            r'C:\docs\고객명단.csv',
          ],
        ),
      ),
    );

    expect(find.text('파일 2개'), findsOneWidget);
    expect(find.text('상담기록.txt'), findsOneWidget);
    expect(find.text('고객명단.csv'), findsOneWidget);
    expect(find.text('비식별화 시작'), findsOneWidget);
    expect(find.text('목록 비우기'), findsOneWidget);
    // 전략 토글 두 개가 표시된다
    expect(find.text(MaskStrategy.mask.displayName), findsOneWidget);
    expect(find.text(MaskStrategy.label.displayName), findsOneWidget);
  });

  testWidgets('파일 찾아보기로 고른 파일이 목록에 추가된다', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          pickFiles: () async => [r'C:\docs\선택한파일.txt'],
        ),
      ),
    );

    await tester.tap(find.text('또는 파일 찾아보기'));
    await tester.pump();

    expect(find.text('선택한파일.txt'), findsOneWidget);
    expect(find.text('파일 1개'), findsOneWidget);
  });

  testWidgets('목록 비우기를 누르면 드롭존만 남는다', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          initialFiles: const [r'C:\docs\상담기록.txt'],
        ),
      ),
    );

    await tester.tap(find.text('목록 비우기'));
    await tester.pump();

    expect(find.text('상담기록.txt'), findsNothing);
    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);
  });

  testWidgets('비식별화 시작을 누르면 완료 상태와 탐지 요약이 표시된다',
      (WidgetTester tester) async {
    // 위젯 테스트는 가짜 시간으로 돌아서 실제 파일 IO가 완료되지 않는다.
    // 파일 생성·처리 대기 등 실제 IO는 전부 runAsync 블록 안에서 돈다.
    late final Directory dir;
    late final String inputPath;
    await tester.runAsync(() async {
      dir = await Directory.systemTemp.createTemp('maskingtape_widget');
      final input = File('${dir.path}${Platform.pathSeparator}상담기록.txt');
      await input.writeAsString('주민번호 800101-1234560 문의주세요');
      inputPath = input.path;
    });

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          initialFiles: [inputPath],
        ),
      ),
    );

    await tester.runAsync(() async {
      await tester.tap(find.text('비식별화 시작'));
      for (var i = 0; i < 100; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
        await tester.pump();
        if (find.byIcon(Icons.check_circle).evaluate().isNotEmpty) {
          break;
        }
      }
      await dir.delete(recursive: true);
    });

    expect(find.byIcon(Icons.check_circle), findsOneWidget);
    expect(find.textContaining('탐지 1건 — 주민번호 1'), findsOneWidget);
    expect(find.textContaining('_masked.txt'), findsOneWidget);

    // 완료 항목을 클릭하면 원문 vs 마스킹 결과 비교 다이얼로그가 뜬다
    await tester.tap(find.text('상담기록.txt'));
    await tester.pumpAndSettle();
    expect(find.text('원문'), findsOneWidget);
    expect(find.text('마스킹 결과'), findsOneWidget);
    expect(find.textContaining('**************'), findsOneWidget);
  });

  testWidgets('라벨 전략을 고르면 백엔드에 그대로 전달된다', (WidgetTester tester) async {
    late final String inputPath;
    await tester.runAsync(() async {
      final dir = await Directory.systemTemp.createTemp('maskingtape_widget');
      final input = File('${dir.path}${Platform.pathSeparator}입력.txt');
      await input.writeAsString('주민번호 800101-1234560');
      inputPath = input.path;
    });

    final fake = FakeAnonymizer();
    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(anonymizer: fake, initialFiles: [inputPath]),
      ),
    );

    await tester.tap(find.text(MaskStrategy.label.displayName));
    await tester.pump();

    await tester.runAsync(() async {
      await tester.tap(find.text('비식별화 시작'));
      for (var i = 0; i < 100; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
        await tester.pump();
        if (find.byIcon(Icons.check_circle).evaluate().isNotEmpty) {
          break;
        }
      }
    });

    expect(fake.lastStrategy, MaskStrategy.label);
  });
}
