// Widget tests for AssenBottomCta (Korean B2C convention #1). Single + split
// layouts, disabled state, tap callbacks. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenBottomCta', () {
    testWidgets('single renders one button and fires it', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(AssenBottomCta(primaryLabel: '예약하기', onPrimary: () => taps++)),
      );
      expect(find.text('예약하기'), findsOneWidget);
      await tester.tap(find.text('예약하기'));
      expect(taps, 1);
    });

    testWidgets('disabled when onPrimary is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenBottomCta(primaryLabel: '다음', onPrimary: null)),
      );
      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      expect(button.onPressed, isNull);
    });

    testWidgets('split renders both actions and fires each', (tester) async {
      var prim = 0;
      var sec = 0;
      await tester.pumpWidget(
        _host(
          AssenBottomCta.split(
            primaryLabel: '다음',
            onPrimary: () => prim++,
            secondaryLabel: '이전',
            onSecondary: () => sec++,
          ),
        ),
      );
      expect(find.text('다음'), findsOneWidget);
      expect(find.text('이전'), findsOneWidget);
      await tester.tap(find.text('이전'));
      await tester.tap(find.text('다음'));
      expect(sec, 1);
      expect(prim, 1);
    });

    testWidgets('primary meets the 44pt minimum touch target', (tester) async {
      await tester.pumpWidget(
        _host(AssenBottomCta(primaryLabel: 'x', onPrimary: () {})),
      );
      final size = tester.getSize(find.byType(FilledButton));
      expect(size.height, greaterThanOrEqualTo(44));
    });
  });

  goldenTest(
    'bottom CTA matches the approved baseline',
    fileName: 'bottom_cta',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'single',
          child: SizedBox(
            width: 360,
            child: AssenBottomCta(primaryLabel: '예약하기', onPrimary: () {}),
          ),
        ),
      ],
    ),
  );
}
