import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/main.dart';
import 'package:maskingtape_desktop/screens/home_screen.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';

import 'fakes.dart';

/// 위젯 테스트는 가짜 시간으로 돌아 실제 파일 IO가 끝나지 않는다.
/// 처리 시작부터 완료(성공/실패 아이콘)까지는 runAsync 안에서 기다린다.
Future<void> _runProcessing(WidgetTester tester) async {
  await tester.runAsync(() async {
    await tester.tap(find.text('비식별화 시작'));
    for (var i = 0; i < 100; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
      await tester.pump();
      final done = find.byIcon(Icons.check_circle).evaluate().isNotEmpty;
      final failed = find.byIcon(Icons.error_outline).evaluate().isNotEmpty;
      if (done || failed) {
        break;
      }
    }
  });
}

/// 합성 내용이 담긴 임시 텍스트 파일을 만든다 (실제 개인정보 없음).
Future<String> _makeTempFile(
  WidgetTester tester,
  String name,
  String content,
) async {
  late final String path;
  await tester.runAsync(() async {
    final dir = await Directory.systemTemp.createTemp('maskingtape_widget');
    final file = File('${dir.path}${Platform.pathSeparator}$name');
    await file.writeAsString(content);
    path = file.path;
  });
  return path;
}

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
    // 전략 토글과 이름 정밀 탐지 토글이 함께 보인다
    expect(find.text(MaskStrategy.mask.displayName), findsOneWidget);
    expect(find.text(MaskStrategy.label.displayName), findsOneWidget);
    expect(find.text('이름 정밀 탐지'), findsOneWidget);
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
    final path = await _makeTempFile(
      tester,
      '상담기록.txt',
      '주민번호 ${FakeAnonymizer.rrn} 문의주세요',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          initialFiles: [path],
        ),
      ),
    );
    await _runProcessing(tester);

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
    final path = await _makeTempFile(
      tester,
      '입력.txt',
      '주민번호 ${FakeAnonymizer.rrn}',
    );
    final fake = FakeAnonymizer();

    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(anonymizer: fake, initialFiles: [path])),
    );
    await tester.tap(find.text(MaskStrategy.label.displayName));
    await tester.pump();
    await _runProcessing(tester);

    expect(fake.lastOptions?.strategy, MaskStrategy.label);
  });

  testWidgets('이름 정밀 탐지는 기본으로 꺼져 있다 (Ollama 없이도 동작)',
      (WidgetTester tester) async {
    final path = await _makeTempFile(
      tester,
      '회의록.txt',
      '참석자 ${FakeAnonymizer.name}, 주민번호 ${FakeAnonymizer.rrn}',
    );
    final fake = FakeAnonymizer();

    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(anonymizer: fake, initialFiles: [path])),
    );
    await _runProcessing(tester);

    expect(fake.lastOptions?.useLlm, isFalse);
    // 규칙 전용이므로 이름은 잡히지 않는다
    expect(find.textContaining('탐지 1건 — 주민번호 1'), findsOneWidget);
  });

  testWidgets('이름 정밀 탐지를 켜면 백엔드에 전달되고 이름까지 탐지된다',
      (WidgetTester tester) async {
    final path = await _makeTempFile(
      tester,
      '회의록.txt',
      '참석자 ${FakeAnonymizer.name}, 주민번호 ${FakeAnonymizer.rrn}',
    );
    final fake = FakeAnonymizer();

    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(anonymizer: fake, initialFiles: [path])),
    );
    await tester.tap(find.text('이름 정밀 탐지'));
    await tester.pump();
    await _runProcessing(tester);

    expect(fake.lastOptions?.useLlm, isTrue);
    expect(find.textContaining('주민번호 1 · 이름 1'), findsOneWidget);
  });

  testWidgets('Ollama가 없으면 그 안내가 실패 사유로 그대로 표시된다',
      (WidgetTester tester) async {
    const ollamaMessage = '로컬 Ollama에 연결하지 못했습니다(http://localhost:11434).';
    final path = await _makeTempFile(tester, '회의록.txt', '참석자 김민서');

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          anonymizer: const FailingAnonymizer(message: ollamaMessage),
          initialFiles: [path],
        ),
      ),
    );
    await tester.tap(find.text('이름 정밀 탐지'));
    await tester.pump();
    await _runProcessing(tester);

    expect(find.byIcon(Icons.error_outline), findsOneWidget);
    expect(find.textContaining(ollamaMessage), findsOneWidget);
  });
}
