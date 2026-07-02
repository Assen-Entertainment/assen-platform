// Widget tests for AssenTextField (default / focused / error / disabled).
// Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenTextField', () {
    testWidgets('renders its label', (tester) async {
      await tester.pumpWidget(_host(const AssenTextField(label: '이름')));
      expect(find.text('이름'), findsOneWidget);
    });

    testWidgets('reports edits via onChanged', (tester) async {
      String? typed;
      await tester.pumpWidget(
        _host(AssenTextField(label: '이름', onChanged: (v) => typed = v)),
      );
      await tester.enterText(find.byType(TextField), '미오');
      expect(typed, '미오');
    });

    testWidgets('shows the error message in the error state', (tester) async {
      await tester.pumpWidget(
        _host(const AssenTextField(label: '이메일', errorText: '형식 오류')),
      );
      expect(find.text('형식 오류'), findsOneWidget);
    });

    testWidgets('disables the field when enabled is false', (tester) async {
      await tester.pumpWidget(
        _host(const AssenTextField(label: '이름', enabled: false)),
      );
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
    });
  });

  goldenTest(
    'text field matches the approved baseline',
    fileName: 'text_field',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'default',
          child: const SizedBox(
            width: 240,
            child: AssenTextField(label: '이름'),
          ),
        ),
        GoldenTestScenario(
          name: 'error',
          child: const SizedBox(
            width: 240,
            child: AssenTextField(label: '이메일', errorText: '형식 오류'),
          ),
        ),
      ],
    ),
  );
}
