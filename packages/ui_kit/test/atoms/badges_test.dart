// Widget tests for AssenBadge / AssenCountBadge / AssenStatusBadge. Pixel
// golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

BoxDecoration _decorationOf(WidgetTester tester, Type ancestor) {
  final container = tester.widget<Container>(
    find.descendant(
      of: find.byType(ancestor),
      matching: find.byType(Container),
    ),
  );
  return container.decoration! as BoxDecoration;
}

void main() {
  group('AssenBadge', () {
    testWidgets('renders its label', (tester) async {
      await tester.pumpWidget(_host(const AssenBadge(label: 'NEW')));
      expect(find.text('NEW'), findsOneWidget);
    });

    testWidgets('sky hue fills with the sky pastel surface', (tester) async {
      await tester.pumpWidget(
        _host(const AssenBadge(label: 'sky', hue: AssenBadgeHue.sky)),
      );
      expect(_decorationOf(tester, AssenBadge).color, RefColors.skyBg);
    });

    testWidgets('sky hue text uses the sky ink step', (tester) async {
      await tester.pumpWidget(
        _host(const AssenBadge(label: 'sky', hue: AssenBadgeHue.sky)),
      );
      final text = tester.widget<Text>(find.text('sky'));
      expect(text.style!.color, RefColors.skyInk);
    });
  });

  group('AssenCountBadge', () {
    testWidgets('shows the exact count', (tester) async {
      await tester.pumpWidget(_host(const AssenCountBadge(count: 7)));
      expect(find.text('7'), findsOneWidget);
    });

    testWidgets('clamps over-max counts to "max+"', (tester) async {
      await tester.pumpWidget(
        _host(const AssenCountBadge(count: 150)),
      );
      expect(find.text('99+'), findsOneWidget);
    });

    testWidgets('renders a dot (no text) for zero', (tester) async {
      await tester.pumpWidget(_host(const AssenCountBadge(count: 0)));
      expect(find.byType(Text), findsNothing);
    });
  });

  group('AssenStatusBadge', () {
    testWidgets('confirmed maps to the matcha surface', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatusBadge(
            kind: AssenStatusKind.confirmed,
            label: '확정',
          ),
        ),
      );
      expect(find.text('확정'), findsOneWidget);
      expect(_decorationOf(tester, AssenStatusBadge).color, RefColors.matchaBg);
    });

    testWidgets('cancelled maps to the red surface', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatusBadge(
            kind: AssenStatusKind.cancelled,
            label: '취소',
          ),
        ),
      );
      expect(_decorationOf(tester, AssenStatusBadge).color, RefColors.redBg);
    });
  });

  goldenTest(
    'badges match the approved baseline',
    fileName: 'badges',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'badge-strawberry',
          child: const AssenBadge(label: 'NEW'),
        ),
        GoldenTestScenario(
          name: 'count-99plus',
          child: const AssenCountBadge(count: 150),
        ),
        GoldenTestScenario(
          name: 'status-confirmed',
          child: const AssenStatusBadge(
            kind: AssenStatusKind.confirmed,
            label: '확정',
          ),
        ),
      ],
    ),
  );
}
