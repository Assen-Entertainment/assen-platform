// Widget tests for AssenStatCard (운영자 지표). Renders value/label and an optional
// trend delta with the matching arrow. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 180, child: child)),
  ),
);

void main() {
  group('AssenStatCard', () {
    testWidgets('renders value and label', (tester) async {
      await tester.pumpWidget(
        _host(const AssenStatCard(value: '1,284', label: '오늘 방문')),
      );
      expect(find.text('1,284'), findsOneWidget);
      expect(find.text('오늘 방문'), findsOneWidget);
    });

    testWidgets('up trend shows the delta and up arrow', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatCard(
            value: '1,284',
            label: '오늘 방문',
            delta: '+12%',
            trend: AssenStatTrend.up,
          ),
        ),
      );
      expect(find.text('+12%'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_upward), findsOneWidget);
    });

    testWidgets('down trend shows the down arrow', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatCard(
            value: '37',
            label: '대기 인원',
            delta: '-4',
            trend: AssenStatTrend.down,
          ),
        ),
      );
      expect(find.byIcon(Icons.arrow_downward), findsOneWidget);
    });
  });

  goldenTest(
    'stat card matches the approved baseline',
    fileName: 'stat_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'up',
          child: const SizedBox(
            width: 180,
            child: AssenStatCard(
              value: '1,284',
              label: '오늘 방문',
              delta: '+12%',
              trend: AssenStatTrend.up,
              icon: Icons.people_outline,
            ),
          ),
        ),
      ],
    ),
  );
}
