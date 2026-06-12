// Smoke + structure test for the T5 operator dashboard template (ASS-88),
// covering the segmented view switch. The pixel golden is declared but skipped
// (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenOperatorDashboardTemplate', () {
    testWidgets('renders the notice, segments, stat grid and booking board', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenOperatorDashboardTemplate(),
        ),
      );

      expect(find.text('운영자 대시보드'), findsOneWidget);
      // The 신고 알림 notice strip.
      expect(find.byType(AssenNoticeBar), findsOneWidget);
      // The operator view switch.
      expect(find.byType(AssenSegmentedTabs), findsOneWidget);
      // The default (현황) segment shows the four metric cards...
      expect(find.byType(AssenStatCard), findsNWidgets(4));
      // ...over the 예약/대기 board rows.
      expect(find.byType(AssenReservationCard), findsNWidgets(3));
    });

    testWidgets('hides the stat grid on the 예약 segment', (tester) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenOperatorDashboardTemplate(),
        ),
      );

      // Switching to the 예약 segment drops the metric grid but keeps the
      // booking board. Scope the tap to the segmented control so the label
      // is unambiguous (other surfaces also contain "예약").
      await tester.tap(
        find.descendant(
          of: find.byType(AssenSegmentedTabs),
          matching: find.text('예약'),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(AssenStatCard), findsNothing);
      expect(find.byType(AssenReservationCard), findsNWidgets(3));
    });

    // Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'operator dashboard template matches the approved baseline',
      fileName: 'operator_dashboard_template',
      skip: true, // baseline pending human approval (#31); golden #31 대기.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'default',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenOperatorDashboardTemplate(),
            ),
          ),
        ],
      ),
    );
  });
}

/// Sizes the test view to a tall phone (375×1200 logical) so the whole
/// scrolling dashboard lays out and the off-screen 예약/대기 board builds.
/// Resets after the test via [addTearDown].
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1125, 3600);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}
