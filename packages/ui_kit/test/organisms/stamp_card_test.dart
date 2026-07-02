// Widget tests for AssenStampCard (모티프). Counter, filled-vs-empty slots, the
// reward slot, and the clamp. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 340, child: child)),
  ),
);

void main() {
  group('AssenStampCard', () {
    testWidgets('renders the title and progress counter', (tester) async {
      await tester.pumpWidget(
        _host(const AssenStampCard(title: '방문 스탬프', filled: 5)),
      );
      expect(find.text('방문 스탬프'), findsOneWidget);
      expect(find.text('5 / 8'), findsOneWidget);
    });

    testWidgets('stamps exactly the filled count with hearts', (tester) async {
      await tester.pumpWidget(
        _host(const AssenStampCard(title: '스탬프', filled: 3)),
      );
      // 3 filled non-reward cells each show a heart (reward slot is index 7).
      expect(find.byIcon(Icons.favorite), findsNWidgets(3));
    });

    testWidgets('clamps an over-full count to the slot total', (tester) async {
      await tester.pumpWidget(
        _host(const AssenStampCard(title: '스탬프', filled: 99)),
      );
      expect(find.text('8 / 8'), findsOneWidget);
      // Fully filled: 7 hearts + 1 redeemed reward glyph.
      expect(find.byIcon(Icons.redeem), findsOneWidget);
      expect(find.byIcon(Icons.favorite), findsNWidgets(7));
    });

    testWidgets('shows the reward label on an unfilled reward slot', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenStampCard(
            title: '스탬프',
            filled: 2,
            rewardLabel: '체키',
          ),
        ),
      );
      expect(find.text('체키'), findsOneWidget);
    });
  });

  goldenTest(
    'stamp card matches the approved baseline',
    fileName: 'stamp_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'half-filled',
          child: const SizedBox(
            width: 340,
            child: AssenStampCard(
              title: '방문 스탬프',
              filled: 5,
              rewardLabel: '체키',
            ),
          ),
        ),
      ],
    ),
  );
}
