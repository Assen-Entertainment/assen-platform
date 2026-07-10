// Widget tests for AssenDivider. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenDivider', () {
    testWidgets('renders a 1px ink-ramp rule', (tester) async {
      await tester.pumpWidget(_host(const AssenDivider()));
      final divider = tester.widget<Divider>(find.byType(Divider));
      expect(divider.color, RefColors.neutral100);
      expect(divider.thickness, 1);
    });

    testWidgets('inset variant carries the indent', (tester) async {
      await tester.pumpWidget(
        _host(const AssenDivider(indent: SpacingTokens.s4)),
      );
      final divider = tester.widget<Divider>(find.byType(Divider));
      expect(divider.indent, SpacingTokens.s4);
    });
  });

  goldenTest(
    'AssenDivider matches the approved baseline',
    fileName: 'divider',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(name: 'full-bleed', child: const AssenDivider()),
        GoldenTestScenario(
          name: 'inset',
          child: const AssenDivider(indent: SpacingTokens.s4),
        ),
      ],
    ),
  );
}
