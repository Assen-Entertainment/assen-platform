// Widget tests for AssenCard. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

BoxDecoration _cardDecoration(WidgetTester tester) {
  final box = tester.widget<DecoratedBox>(
    find
        .descendant(
          of: find.byType(AssenCard),
          matching: find.byType(DecoratedBox),
        )
        .first,
  );
  return box.decoration as BoxDecoration;
}

void main() {
  group('AssenCard', () {
    testWidgets('renders its child', (tester) async {
      await tester.pumpWidget(
        _host(const AssenCard(child: Text('hello'))),
      );
      expect(find.text('hello'), findsOneWidget);
    });

    testWidgets('level0 draws a border and no shadow', (tester) async {
      await tester.pumpWidget(
        _host(const AssenCard(child: Text('x'))),
      );
      final decoration = _cardDecoration(tester);
      expect(decoration.border, isNotNull);
      expect(decoration.boxShadow, isNull);
    });

    testWidgets('level1 draws a shadow and no border', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCard(level: AssenCardLevel.level1, child: Text('x')),
        ),
      );
      final decoration = _cardDecoration(tester);
      expect(decoration.boxShadow, isNotNull);
      expect(decoration.boxShadow!.first.color, ElevationTokens.level1Color);
      expect(decoration.border, isNull);
    });

    testWidgets('is tappable when onTap is set', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(AssenCard(onTap: () => taps++, child: const Text('tap'))),
      );
      await tester.tap(find.byType(AssenCard));
      expect(taps, 1);
    });
  });

  goldenTest(
    'AssenCard matches the approved baseline',
    fileName: 'card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'level0',
          child: const AssenCard(child: Text('level0')),
        ),
        GoldenTestScenario(
          name: 'level1',
          child: const AssenCard(
            level: AssenCardLevel.level1,
            child: Text('level1'),
          ),
        ),
      ],
    ),
  );
}
