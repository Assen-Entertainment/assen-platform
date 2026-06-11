// Widget tests for AssenStepper (default / min / max). The value is clamped to
// [min, max] and the matching button disables at each bound. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenStepper', () {
    testWidgets('renders the current value', (tester) async {
      await tester.pumpWidget(
        _host(AssenStepper(value: 3, onChanged: (_) {})),
      );
      expect(find.text('3'), findsOneWidget);
    });

    testWidgets('increments on +', (tester) async {
      int? next;
      await tester.pumpWidget(
        _host(AssenStepper(value: 2, onChanged: (v) => next = v)),
      );
      await tester.tap(find.byIcon(Icons.add));
      expect(next, 3);
    });

    testWidgets('decrements on -', (tester) async {
      int? next;
      await tester.pumpWidget(
        _host(AssenStepper(value: 2, onChanged: (v) => next = v)),
      );
      await tester.tap(find.byIcon(Icons.remove));
      expect(next, 1);
    });

    testWidgets('disables - at min and + at max', (tester) async {
      await tester.pumpWidget(
        _host(AssenStepper(value: 1, max: 1, onChanged: (_) {})),
      );
      final remove = tester.widget<IconButton>(
        find.ancestor(
          of: find.byIcon(Icons.remove),
          matching: find.byType(IconButton),
        ),
      );
      final add = tester.widget<IconButton>(
        find.ancestor(
          of: find.byIcon(Icons.add),
          matching: find.byType(IconButton),
        ),
      );
      expect(remove.onPressed, isNull);
      expect(add.onPressed, isNull);
    });
  });

  goldenTest(
    'stepper matches the approved baseline',
    fileName: 'stepper',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'default',
          child: AssenStepper(value: 2, onChanged: (_) {}),
        ),
      ],
    ),
  );
}
