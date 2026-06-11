// Widget tests for AssenSectionHeader (액션 유/무). The action label + chevron
// appear only when both label and handler are given. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenSectionHeader', () {
    testWidgets('renders the title', (tester) async {
      await tester.pumpWidget(
        _host(const AssenSectionHeader(title: '획득한 체키')),
      );
      expect(find.text('획득한 체키'), findsOneWidget);
    });

    testWidgets('shows no action when title-only', (tester) async {
      await tester.pumpWidget(
        _host(const AssenSectionHeader(title: '획득한 체키')),
      );
      expect(find.byIcon(Icons.chevron_right), findsNothing);
    });

    testWidgets('fires onAction via the action', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _host(
          AssenSectionHeader(
            title: '획득한 체키',
            actionLabel: '전체보기',
            onAction: () => tapped = true,
          ),
        ),
      );
      await tester.tap(find.text('전체보기'));
      expect(tapped, isTrue);
    });
  });

  goldenTest(
    'section header matches the approved baseline',
    fileName: 'section_header',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-action',
          child: SizedBox(
            width: 320,
            child: AssenSectionHeader(
              title: '획득한 체키',
              actionLabel: '전체보기',
              onAction: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
