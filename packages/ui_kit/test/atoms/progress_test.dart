// Widget tests for AssenProgressBar / AssenProgressDonut / AssenPageIndicator.
// Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenProgressBar', () {
    testWidgets('passes its value to the indicator', (tester) async {
      await tester.pumpWidget(_host(const AssenProgressBar(value: 0.4)));
      final bar = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(bar.value, 0.4);
    });

    testWidgets('clamps an out-of-range value', (tester) async {
      await tester.pumpWidget(_host(const AssenProgressBar(value: 1.8)));
      final bar = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(bar.value, 1.0);
    });

    testWidgets('fills with the rose anchor', (tester) async {
      await tester.pumpWidget(_host(const AssenProgressBar(value: 0.5)));
      final bar = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(bar.valueColor!.value, RefColors.indigo500);
    });
  });

  group('AssenProgressDonut', () {
    testWidgets('paints a ring via CustomPaint', (tester) async {
      await tester.pumpWidget(_host(const AssenProgressDonut(value: 0.625)));
      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders the centre widget in the hole', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenProgressDonut(value: 0.5, center: Text('5/8')),
        ),
      );
      expect(find.text('5/8'), findsOneWidget);
    });
  });

  group('AssenPageIndicator', () {
    testWidgets('renders one dot per page', (tester) async {
      await tester.pumpWidget(
        _host(const AssenPageIndicator(count: 4, activeIndex: 0)),
      );
      expect(find.byType(AnimatedContainer), findsNWidgets(4));
    });

    testWidgets('active dot is the rose anchor', (tester) async {
      await tester.pumpWidget(
        _host(const AssenPageIndicator(count: 3, activeIndex: 1)),
      );
      final dots = tester
          .widgetList<AnimatedContainer>(find.byType(AnimatedContainer))
          .toList();
      final activeColor = (dots[1].decoration! as BoxDecoration).color;
      expect(activeColor, RefColors.indigo500);
    });
  });

  goldenTest(
    'progress indicators match the approved baseline',
    fileName: 'progress',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'bar',
          child: const SizedBox(
            width: 200,
            child: AssenProgressBar(value: 0.4),
          ),
        ),
        GoldenTestScenario(
          name: 'donut',
          child: const AssenProgressDonut(value: 0.625),
        ),
        GoldenTestScenario(
          name: 'page-indicator',
          child: const AssenPageIndicator(count: 4, activeIndex: 1),
        ),
      ],
    ),
  );
}
