// Widget tests for AssenSkeleton. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenSkeleton', () {
    testWidgets('renders a sized block', (tester) async {
      await tester.pumpWidget(
        _host(const AssenSkeleton(width: 120, height: 20)),
      );
      expect(find.byType(AssenSkeleton), findsOneWidget);
      final box = tester.getSize(
        find
            .descendant(
              of: find.byType(AssenSkeleton),
              matching: find.byType(SizedBox),
            )
            .first,
      );
      expect(box.width, 120);
      expect(box.height, 20);
    });

    testWidgets('animates without throwing (pump through a frame)', (
      tester,
    ) async {
      await tester.pumpWidget(_host(const AssenSkeleton(width: 80)));
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(AssenSkeleton), findsOneWidget);
    });

    testWidgets('honours reduced motion', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const MediaQuery(
            data: MediaQueryData(disableAnimations: true),
            child: Scaffold(body: Center(child: AssenSkeleton(width: 80))),
          ),
        ),
      );
      // Animations disabled -> the skeleton's own animated branch is absent.
      final animatedInside = find.descendant(
        of: find.byType(AssenSkeleton),
        matching: find.byType(AnimatedBuilder),
      );
      expect(animatedInside, findsNothing);
    });
  });

  goldenTest(
    'AssenSkeleton matches the approved baseline',
    fileName: 'skeleton',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'line',
          child: const AssenSkeleton(width: 180),
        ),
      ],
    ),
  );
}
