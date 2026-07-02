// Smoke + structure test for the T2 schedule template (ASS-88). The pixel
// golden is declared but skipped (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenScheduleTemplate', () {
    testWidgets('renders the weekly board with filters and cast slots', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenScheduleTemplate(),
        ),
      );

      // Scope the title to the app bar; the bottom tab bar also has a
      // "출근표" label.
      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('출근표'),
        ),
        findsOneWidget,
      );
      expect(find.byType(AssenScheduleCalendar), findsOneWidget);
      // The 최애 filter chips render (전체 + 4 fictional cast names).
      expect(find.byType(AssenFilterChip), findsNWidgets(5));
      // The selected day (today = 수, index 2) lists three cast slots.
      expect(find.byType(AssenCastProfileCard), findsNWidgets(3));
      expect(find.byType(AssenTabBar), findsOneWidget);
    });

    testWidgets('swaps the cast slot list when another day is selected', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenScheduleTemplate(),
        ),
      );

      // Tapping 월요일 (one cast) reduces the slot list from three to one.
      await tester.tap(find.text('9'));
      await tester.pumpAndSettle();
      expect(find.byType(AssenCastProfileCard), findsOneWidget);
    });

    // Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'schedule template matches the approved baseline',
      fileName: 'schedule_template',
      skip: true, // baseline pending human approval (#31); golden #31 대기.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'default',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenScheduleTemplate(),
            ),
          ),
        ],
      ),
    );
  });
}

/// Sizes the test view to a tall phone (375×1200 logical) so the whole
/// scrolling board lays out and the off-screen cast slots build. Resets
/// after the test via [addTearDown].
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1125, 3600);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}
