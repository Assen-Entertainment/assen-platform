// Widget tests for AssenLogo (brand lockup). Wordmark rendering per variant and
// the accessibility label. Pixel golden deferred (#31).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenLogo', () {
    testWidgets('full lockup renders the wordmark', (tester) async {
      await tester.pumpWidget(_host(const AssenLogo()));
      expect(find.text('Assen'), findsOneWidget);
    });

    testWidgets('mark-only omits the wordmark but keeps the a11y label', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(const AssenLogo(variant: AssenLogoVariant.mark)),
      );
      expect(find.text('Assen'), findsNothing);
      expect(find.bySemanticsLabel('Assen'), findsOneWidget);
    });

    testWidgets('mono full lockup still renders the wordmark', (tester) async {
      await tester.pumpWidget(
        _host(const AssenLogo(mono: true, color: Color(0xFFFFFFFF))),
      );
      expect(find.text('Assen'), findsOneWidget);
    });
  });
}
