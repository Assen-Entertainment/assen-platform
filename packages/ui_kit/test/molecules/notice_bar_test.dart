// Widget tests for AssenNoticeBar (info / warning). Message renders and each
// kind picks its default glyph. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenNoticeBar', () {
    testWidgets('renders the message', (tester) async {
      await tester.pumpWidget(
        _host(const AssenNoticeBar(message: '오늘은 11:00에 엽니다.')),
      );
      expect(find.text('오늘은 11:00에 엽니다.'), findsOneWidget);
    });

    testWidgets('info uses the info glyph', (tester) async {
      await tester.pumpWidget(
        _host(const AssenNoticeBar(message: '공지')),
      );
      expect(find.byIcon(Icons.info_outline), findsOneWidget);
    });

    testWidgets('warning uses the warning glyph', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenNoticeBar(
            message: '마감 임박',
            kind: AssenNoticeKind.warning,
          ),
        ),
      );
      expect(find.byIcon(Icons.warning_amber_outlined), findsOneWidget);
    });
  });

  goldenTest(
    'notice bar matches the approved baseline',
    fileName: 'notice_bar',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'warning',
          child: const SizedBox(
            width: 320,
            child: AssenNoticeBar(
              message: '예약 마감이 임박했습니다.',
              kind: AssenNoticeKind.warning,
            ),
          ),
        ),
      ],
    ),
  );
}
