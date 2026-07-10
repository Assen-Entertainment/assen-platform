// Widget tests for AssenReveal (entry motion). The key contract is a11y: when
// the platform reports reduced motion, the reveal renders its child directly
// with no fade/slide wrapper at all (WCAG 2.3.3).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host({required bool reduceMotion, required Widget child}) => MediaQuery(
  data: MediaQueryData(disableAnimations: reduceMotion),
  child: Directionality(textDirection: TextDirection.ltr, child: child),
);

void main() {
  group('AssenReveal', () {
    testWidgets('animates with a fade/slide when motion is allowed', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          reduceMotion: false,
          child: const AssenReveal(child: Text('hi')),
        ),
      );
      expect(find.text('hi'), findsOneWidget);
      // The reveal wraps the child in an Opacity during the animation.
      expect(
        find.descendant(
          of: find.byType(AssenReveal),
          matching: find.byType(Opacity),
        ),
        findsWidgets,
      );
    });

    testWidgets('renders the child directly under reduced motion', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          reduceMotion: true,
          child: const AssenReveal(child: Text('hi')),
        ),
      );
      expect(find.text('hi'), findsOneWidget);
      // No fade/slide wrapper: the child is returned as-is.
      expect(
        find.descendant(
          of: find.byType(AssenReveal),
          matching: find.byType(Opacity),
        ),
        findsNothing,
      );
    });
  });
}
