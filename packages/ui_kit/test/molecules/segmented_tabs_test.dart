// Widget tests for AssenSegmentedTabs (selected / unselected). Reports the
// tapped index. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenSegmentedTabs', () {
    testWidgets('renders all segment labels', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenSegmentedTabs(
            segments: const ['대기', '예약'],
            selectedIndex: 0,
            onChanged: (_) {},
          ),
        ),
      );
      expect(find.text('대기'), findsOneWidget);
      expect(find.text('예약'), findsOneWidget);
    });

    testWidgets('reports the tapped index', (tester) async {
      int? index;
      await tester.pumpWidget(
        _host(
          AssenSegmentedTabs(
            segments: const ['대기', '예약'],
            selectedIndex: 0,
            onChanged: (i) => index = i,
          ),
        ),
      );
      await tester.tap(find.text('예약'));
      expect(index, 1);
    });
  });

  goldenTest(
    'segmented tabs match the approved baseline',
    fileName: 'segmented_tabs',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'selected-first',
          child: SizedBox(
            width: 280,
            child: AssenSegmentedTabs(
              segments: const ['대기', '예약'],
              selectedIndex: 0,
              onChanged: (_) {},
            ),
          ),
        ),
      ],
    ),
  );
}
