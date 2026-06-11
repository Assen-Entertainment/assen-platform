// Widget tests for AssenKeyValueRow (기본 / 강조). Both label and value render;
// the emphasis variant restyles the value. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenKeyValueRow', () {
    testWidgets('renders label and value', (tester) async {
      await tester.pumpWidget(
        _host(const AssenKeyValueRow(label: '결제 금액', value: '₩12,000')),
      );
      expect(find.text('결제 금액'), findsOneWidget);
      expect(find.text('₩12,000'), findsOneWidget);
    });

    testWidgets('emphasis variant still renders the value', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenKeyValueRow(
            label: '합계',
            value: '₩30,000',
            emphasis: true,
          ),
        ),
      );
      expect(find.text('₩30,000'), findsOneWidget);
    });
  });

  goldenTest(
    'key value row matches the approved baseline',
    fileName: 'key_value_row',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'emphasis',
          child: const SizedBox(
            width: 320,
            child: AssenKeyValueRow(
              label: '결제 금액',
              value: '₩12,000',
              emphasis: true,
            ),
          ),
        ),
      ],
    ),
  );
}
