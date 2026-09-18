import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/screens/home_screen.dart';
import 'package:maskingtape_desktop/screens/text_screen.dart';
import 'package:maskingtape_desktop/services/anonymizer.dart';
import 'package:maskingtape_desktop/services/llm_status.dart';
import 'package:maskingtape_desktop/theme.dart';

import 'fakes.dart';

/// 텍스트 화면을 옵션 상태와 함께 띄운다 — 홈 화면이 하는 역할을 테스트용으로 흉내 낸다.
Widget _host(Anonymizer anonymizer, {AnonymizeOptions? initial}) {
  var options = initial ?? const AnonymizeOptions();
  return MaterialApp(
    theme: AppTheme.light(),
    home: StatefulBuilder(
      builder: (context, setState) => Scaffold(
        body: TextScreen(
          anonymizer: anonymizer,
          options: options,
          onOptionsChanged: (o) => setState(() => options = o),
        ),
      ),
    ),
  );
}

// 합성 문장 — 실제 개인정보 없음.
const _sentence = '신청자 주민등록번호 ${FakeAnonymizer.rrn} 확인';

void main() {
  testWidgets('텍스트를 넣기 전에는 실행 버튼이 비활성이고 안내가 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));

    expect(find.text('문서 입력'), findsOneWidget);
    expect(find.text('탐지 결과'), findsOneWidget);
    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '텍스트 입력 필요'),
    );
    expect(button.onPressed, isNull);
    expect(find.textContaining('왼쪽에 텍스트를 입력하고'), findsOneWidget);
  });

  testWidgets('문장을 넣고 실행하면 마스킹 결과와 탐지 목록이 나온다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));

    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    expect(find.text('${_sentence.length} / 100,000자'), findsOneWidget);

    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    // 왼쪽: 마스킹 결과(입력 상자는 사라진다)
    expect(find.text('마스킹 결과'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    expect(
      find.textContaining('*' * FakeAnonymizer.rrn.length),
      findsOneWidget,
    );
    // 오른쪽: 건수 배지 + 종류·값 행
    expect(find.text('탐지 결과 조정'), findsOneWidget);
    expect(find.text('총 1건 발견'), findsOneWidget);
    expect(find.text('개인정보 1건 발견 · 1건 가림 · 0건 노출'), findsOneWidget);
    expect(find.text('주민번호'), findsOneWidget);
    expect(find.text(FakeAnonymizer.rrn), findsOneWidget);
    expect(find.text('100%'), findsOneWidget);
  });

  testWidgets('결과에서 원문 보기로 바꾸면 하이라이트된 원문이 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('원문'));
    await tester.pumpAndSettle();

    expect(find.text('원문 (탐지 하이라이트)'), findsOneWidget);
    // 원문이 그대로 있고(주민번호 포함), 별표 문자열은 없다.
    expect(find.textContaining(FakeAnonymizer.rrn), findsWidgets);
    expect(find.textContaining('*' * FakeAnonymizer.rrn.length), findsNothing);
  });

  testWidgets('다시 입력을 누르면 문장이 남은 채 입력 상자로 돌아간다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('다시 입력'));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, _sentence);
  });

  testWidgets('초기화 하기를 누르면 문장과 결과가 모두 비워진다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('초기화 하기'));
    await tester.pumpAndSettle();

    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      isEmpty,
    );
    expect(find.text('0 / 100,000자'), findsOneWidget);
    expect(find.textContaining('왼쪽에 텍스트를 입력하고'), findsOneWidget);
  });

  testWidgets('샘플 버튼을 누르면 합성 예시 문장이 채워진다', (WidgetTester tester) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));

    await tester.tap(find.text('신청서 샘플'));
    await tester.pump();

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, contains('신청자 김민수'));
  });

  testWidgets('전략을 라벨로 바꾸면 백엔드에 전달되고, 결과가 떠 있으면 다시 돌린다', (
    WidgetTester tester,
  ) async {
    final fake = FakeAnonymizer();
    await tester.pumpWidget(_host(fake));
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();
    expect(fake.lastOptions?.strategy, MaskStrategy.mask);

    await tester.tap(find.text(MaskStrategy.label.displayName));
    await tester.pumpAndSettle();

    expect(fake.lastOptions?.strategy, MaskStrategy.label);
    expect(find.textContaining('[주민등록번호]'), findsOneWidget);
  });

  testWidgets('백엔드 실패 안내가 입력 상자 아래에 그대로 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(
      _host(const FailingAnonymizer(message: 'Ollama가 실행 중이 아닙니다')),
    );
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    expect(find.text('Ollama가 실행 중이 아닙니다'), findsOneWidget);
    // 실패해도 입력은 남아 고쳐서 다시 시도할 수 있다.
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('항목을 「보임」으로 바꾸면 결과 텍스트에 원문이 남고 요약이 바뀐다', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_host(FakeAnonymizer()));
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('*' * FakeAnonymizer.rrn.length),
      findsOneWidget,
    );

    await tester.tap(find.text('가림'));
    await tester.pumpAndSettle();

    expect(find.text('보임'), findsOneWidget);
    expect(find.text('개인정보 1건 발견 · 0건 가림 · 1건 노출'), findsOneWidget);
    // 결과 본문에 주민번호가 그대로 보인다(목록 행의 값과 합쳐 두 곳).
    expect(find.textContaining(FakeAnonymizer.rrn), findsNWidgets(2));
    expect(find.textContaining('*' * FakeAnonymizer.rrn.length), findsNothing);

    // 다시 「가림」으로 돌리면 원래대로.
    await tester.tap(find.text('보임'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('*' * FakeAnonymizer.rrn.length),
      findsOneWidget,
    );
  });

  testWidgets('카테고리별 정렬로 바꾸면 종류명 가나다순으로 나열된다', (WidgetTester tester) async {
    await tester.pumpWidget(
      _host(FakeAnonymizer(), initial: const AnonymizeOptions(useLlm: true)),
    );
    // 이름(김민서)이 주민번호보다 앞에 있는 문장 — 순서대로면 이름이 먼저다.
    await tester.enterText(
      find.byType(TextField),
      '참석자 ${FakeAnonymizer.name}, 주민번호 ${FakeAnonymizer.rrn}',
    );
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    double yOf(String label) => tester.getTopLeft(find.text(label)).dy;
    expect(yOf('이름'), lessThan(yOf('주민번호')));

    await tester.tap(find.text('카테고리별'));
    await tester.pumpAndSettle();
    // 가나다순: 이름(ㅇ) 뒤에 주민번호(ㅈ) — 여전히 이름이 먼저.
    expect(yOf('이름'), lessThan(yOf('주민번호')));

    await tester.tap(find.text('순서대로'));
    await tester.pumpAndSettle();
    expect(yOf('이름'), lessThan(yOf('주민번호')));
  });

  testWidgets('가명 전략에서는 항목별 토글이 꺼지고 안내가 보인다', (WidgetTester tester) async {
    await tester.pumpWidget(
      _host(
        FakeAnonymizer(),
        initial: const AnonymizeOptions(strategy: MaskStrategy.pseudonym),
      ),
    );
    await tester.enterText(find.byType(TextField), _sentence);
    await tester.pump();
    await tester.tap(find.text('개인정보 탐지 및 마스킹 하기'));
    await tester.pumpAndSettle();

    expect(find.textContaining('항목별 가림·노출 조정을 지원하지 않습니다'), findsOneWidget);
    await tester.tap(find.text('가림'));
    await tester.pumpAndSettle();
    // 눌러도 바뀌지 않는다.
    expect(find.text('가림'), findsOneWidget);
    expect(find.text('보임'), findsNothing);
  });

  testWidgets('홈 화면 툴바에서 텍스트 입력 모드로 전환된다', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: HomeScreen(
          anonymizer: FakeAnonymizer(),
          checkLlmStatus: () async => const LlmStatus(LlmReadiness.offline),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);

    await tester.tap(find.text('텍스트 입력'));
    await tester.pumpAndSettle();

    expect(find.text('문서 입력'), findsOneWidget);
    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsNothing);

    await tester.tap(find.text('파일 일괄'));
    await tester.pumpAndSettle();
    expect(find.text('파일을 여기로 끌어다 놓으세요'), findsOneWidget);
  });
}
