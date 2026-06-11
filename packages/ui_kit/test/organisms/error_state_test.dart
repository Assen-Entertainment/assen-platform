// Widget tests for AssenErrorState. Copy, retry vs. no-retry, and the retry
// callback. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenErrorState', () {
    testWidgets('renders title and message', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenErrorState(
            title: '불러오지 못했어요',
            message: '네트워크 상태를 확인해 주세요.',
          ),
        ),
      );
      expect(find.text('불러오지 못했어요'), findsOneWidget);
      expect(find.text('네트워크 상태를 확인해 주세요.'), findsOneWidget);
    });

    testWidgets('shows no retry when onRetry is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenErrorState(title: '오류', message: '복구 불가')),
      );
      expect(find.byType(AssenButton), findsNothing);
    });

    testWidgets('renders and fires the retry CTA', (tester) async {
      var retries = 0;
      await tester.pumpWidget(
        _host(
          AssenErrorState(
            title: '불러오지 못했어요',
            message: '다시 시도해 주세요.',
            onRetry: () => retries++,
          ),
        ),
      );
      expect(find.text('다시 시도'), findsOneWidget);
      await tester.tap(find.text('다시 시도'));
      expect(retries, 1);
    });
  });

  goldenTest(
    'error state matches the approved baseline',
    fileName: 'error_state',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-retry',
          child: SizedBox(
            width: 360,
            height: 360,
            child: AssenErrorState(
              title: '불러오지 못했어요',
              message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
              onRetry: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
