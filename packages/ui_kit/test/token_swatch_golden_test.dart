// Golden infrastructure proof for ASS-128 (alchemist).
//
// SPIKE SCOPE: this proves the golden harness + theme + token pipeline wire up
// end-to-end, while the PIXEL baseline stays human-gated (#31). It does so two
// ways:
//   1. `testWidgets` pumps the token swatch under the Assen theme and
//      asserts the GENERATED token actually renders — exercising
//      tokens.json -> Style Dictionary -> Dart -> Flutter -> pixels.
//   2. `goldenTest(..., skip: ...)` declares the pixel golden but skips it:
//      the baseline PNG requires `flutter test --update-goldens`, which is a
//      human action (CONSTRAINTS #31, guard.py). Once a human approves and
//      generates packages/ui_kit/test/goldens/**, drop the `skip`.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('TokenSwatch golden infra', () {
    // (1) Harness/theme/token pipeline proof — runs and passes today.
    testWidgets('renders the generated rose token under the Assen theme', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const Scaffold(
            body: Center(
              child: TokenSwatch(color: RefColors.indigo500, label: 'rose'),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // The swatch is present and themed from the generated ColorScheme.
      expect(find.text('rose'), findsOneWidget);
      final ctx = tester.element(find.byType(TokenSwatch));
      expect(Theme.of(ctx).colorScheme.primary, RefColors.indigo500);

      // The generated fill colour reached an actual painted Container.
      final decorated = tester.widget<Container>(
        find.descendant(
          of: find.byType(TokenSwatch),
          matching: find.byType(Container),
        ),
      );
      final decoration = decorated.decoration! as BoxDecoration;
      expect(decoration.color, RefColors.indigo500);
    });

    // (2) Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'token swatch row matches the approved baseline',
      fileName: 'token_swatch_row',
      skip: true, // baseline pending human approval (#31); see file header.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'rose',
            child: const TokenSwatch(color: RefColors.indigo500, label: 'rose'),
          ),
          GoldenTestScenario(
            name: 'sky.bg',
            child: const TokenSwatch(color: RefColors.skyBg, label: 'sky.bg'),
          ),
        ],
      ),
    );
  });
}
