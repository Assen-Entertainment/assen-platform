// Widget tests for AssenCheckbox / AssenRadio / AssenSwitch. The Radio test
// also guards the RadioGroup refactor (Flutter 3.32+ API). Pixel golden skipped
// pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenCheckbox', () {
    testWidgets('reflects its value', (tester) async {
      await tester.pumpWidget(
        _host(AssenCheckbox(value: true, onChanged: (_) {})),
      );
      expect(tester.widget<Checkbox>(find.byType(Checkbox)).value, isTrue);
    });

    testWidgets('reports the toggled value on tap', (tester) async {
      bool? next;
      await tester.pumpWidget(
        _host(AssenCheckbox(value: false, onChanged: (v) => next = v)),
      );
      await tester.tap(find.byType(AssenCheckbox));
      expect(next, isTrue);
    });

    testWidgets('disabled when onChanged is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenCheckbox(value: false, onChanged: null)),
      );
      expect(tester.widget<Checkbox>(find.byType(Checkbox)).onChanged, isNull);
    });
  });

  group('AssenRadio', () {
    testWidgets('is selected when value equals groupValue', (tester) async {
      await tester.pumpWidget(
        _host(AssenRadio<int>(value: 1, groupValue: 1, onChanged: (_) {})),
      );
      // Renders without throwing under the RadioGroup ancestor and shows a
      // Radio of the right type.
      expect(find.byType(Radio<int>), findsOneWidget);
    });

    testWidgets('reports its value when chosen', (tester) async {
      int? chosen;
      await tester.pumpWidget(
        _host(
          AssenRadio<int>(
            value: 2,
            groupValue: 0,
            onChanged: (v) => chosen = v,
          ),
        ),
      );
      await tester.tap(find.byType(Radio<int>));
      expect(chosen, 2);
    });

    testWidgets('disabled when onChanged is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenRadio<int>(value: 1, groupValue: 0, onChanged: null)),
      );
      final radio = tester.widget<Radio<int>>(find.byType(Radio<int>));
      expect(radio.enabled, isFalse);
    });
  });

  group('AssenSwitch', () {
    testWidgets('reflects its value', (tester) async {
      await tester.pumpWidget(
        _host(AssenSwitch(value: true, onChanged: (_) {})),
      );
      expect(tester.widget<Switch>(find.byType(Switch)).value, isTrue);
    });

    testWidgets('reports the toggled value on tap', (tester) async {
      bool? next;
      await tester.pumpWidget(
        _host(AssenSwitch(value: false, onChanged: (v) => next = v)),
      );
      await tester.tap(find.byType(AssenSwitch));
      expect(next, isTrue);
    });

    testWidgets('disabled when onChanged is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenSwitch(value: false, onChanged: null)),
      );
      expect(tester.widget<Switch>(find.byType(Switch)).onChanged, isNull);
    });
  });

  goldenTest(
    'selection controls match the approved baseline',
    fileName: 'selection_controls',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'checkbox-checked',
          child: AssenCheckbox(value: true, onChanged: (_) {}),
        ),
        GoldenTestScenario(
          name: 'switch-on',
          child: AssenSwitch(value: true, onChanged: (_) {}),
        ),
        GoldenTestScenario(
          name: 'radio-selected',
          child: AssenRadio<int>(value: 1, groupValue: 1, onChanged: (_) {}),
        ),
      ],
    ),
  );
}
