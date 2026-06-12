// Smoke + structure test for the T1 home template (ASS-88). Rendering the
// assembled screen under the Assen theme exercises the membership/stamp/
// schedule organisms together — the lightweight stand-in for the
// `flutter build web` catalogue smoke on WSL2. The pixel golden is declared
// but skipped (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenHomeTemplate', () {
    testWidgets('renders the home skeleton with its hero components', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenHomeTemplate(),
        ),
      );

      // The app bar title plus the assembled hero organisms confirm the
      // screen built and laid out without throwing.
      expect(find.text('하츠코이'), findsWidgets);
      expect(find.byType(AssenMembershipCard), findsOneWidget);
      expect(find.byType(AssenStampCard), findsOneWidget);
      expect(find.byType(AssenScheduleCalendar), findsOneWidget);
      expect(find.byType(AssenBannerCard), findsOneWidget);
      // The bottom 5-tab chrome is present (Korean B2C convention #1).
      expect(find.byType(AssenTabBar), findsOneWidget);
    });

    testWidgets('shows the unified placeholder member data', (tester) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenHomeTemplate(),
        ),
      );

      // The unified mock surfaces on the membership card.
      expect(find.text('체리체리'), findsWidgets);
      expect(find.text('HK-0042'), findsOneWidget);
      // Stamp counter reads the 5/8 placeholder.
      expect(find.text('5 / 8'), findsOneWidget);
    });

    testWidgets('overrides member data through parameters', (tester) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenHomeTemplate(
            memberName: '미오',
            memberNumber: 'HK-9999',
            stampsFilled: 3,
          ),
        ),
      );

      expect(find.text('HK-9999'), findsOneWidget);
      expect(find.text('3 / 8'), findsOneWidget);
    });

    // Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'home template matches the approved baseline',
      fileName: 'home_template',
      skip: true, // baseline pending human approval (#31); golden #31 대기.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'default',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenHomeTemplate(),
            ),
          ),
        ],
      ),
    );
  });
}

/// Sizes the test view to a tall phone (375×1200 logical) so the whole
/// scrolling template lays out and every off-screen sliver builds. Resets
/// after the test via [addTearDown].
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1125, 3600);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}
