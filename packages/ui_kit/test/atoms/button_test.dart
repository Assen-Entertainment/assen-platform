// Widget tests for AssenButton. Real render/variant/interaction assertions run
// green; the pixel golden is declared but skipped pending human baseline
// approval (#31) — see the goldens/ note file.

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
  group('AssenButton', () {
    testWidgets('renders its label', (tester) async {
      await tester.pumpWidget(
        _host(AssenButton(label: '예약', onPressed: () {})),
      );
      expect(find.text('예약'), findsOneWidget);
    });

    testWidgets('primary fills with the rose action anchor', (tester) async {
      await tester.pumpWidget(
        _host(AssenButton(label: 'go', onPressed: () {})),
      );
      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      final bg = button.style!.backgroundColor!.resolve({});
      expect(bg, RefColors.roseMain);
    });

    testWidgets('ghost variant uses a TextButton', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenButton(
            label: '취소',
            style: AssenButtonStyle.ghost,
            onPressed: () {},
          ),
        ),
      );
      expect(find.byType(TextButton), findsOneWidget);
      expect(find.byType(FilledButton), findsNothing);
    });

    testWidgets('disabled when onPressed is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenButton(label: 'off', onPressed: null)),
      );
      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      expect(button.onPressed, isNull);
    });

    testWidgets('invokes onPressed on tap', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(AssenButton(label: 'tap', onPressed: () => taps++)),
      );
      await tester.tap(find.byType(AssenButton));
      expect(taps, 1);
    });

    testWidgets('meets the 44pt minimum touch target', (tester) async {
      await tester.pumpWidget(_host(AssenButton(label: 'x', onPressed: () {})));
      final size = tester.getSize(find.byType(FilledButton));
      expect(size.height, greaterThanOrEqualTo(44));
    });
  });

  // Pixel golden — baseline pending human approval (#31). Infra-only: proves
  // the golden test is collected and skipped, not that pixels match.
  goldenTest(
    'AssenButton variants match the approved baseline',
    fileName: 'button_variants',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'primary',
          child: AssenButton(label: '예약', onPressed: () {}),
        ),
        GoldenTestScenario(
          name: 'secondary',
          child: AssenButton(
            label: '둘러보기',
            style: AssenButtonStyle.secondary,
            onPressed: () {},
          ),
        ),
        GoldenTestScenario(
          name: 'disabled',
          child: const AssenButton(label: '비활성', onPressed: null),
        ),
      ],
    ),
  );
}
