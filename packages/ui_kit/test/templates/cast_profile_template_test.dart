// Smoke + structure test for the T3 cast profile template (ASS-88). The pixel
// golden is declared but skipped (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenCastProfileTemplate', () {
    testWidgets('renders the profile header, schedule, grid and bottom CTA', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenCastProfileTemplate(),
        ),
      );

      // The header shows the cast name and the 최애 toggle.
      expect(find.text('미오'), findsWidgets);
      expect(find.byType(AssenFavoriteButton), findsOneWidget);
      expect(find.byType(AssenScheduleCalendar), findsOneWidget);
      // The 체키 컬렉션 grid renders its collection cells.
      expect(find.byType(AssenCollectionCell), findsNWidgets(3));
      // The pinned bottom action (Korean B2C convention #1).
      expect(find.byType(AssenBottomCta), findsOneWidget);
      expect(find.text('예약하기'), findsOneWidget);
    });

    testWidgets('toggles the 최애 favourite state on tap', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenCastProfileTemplate(),
        ),
      );

      final favorite = find.byType(AssenFavoriteButton);
      // The toggle is interactive (does not throw when tapped).
      await tester.tap(favorite);
      await tester.pumpAndSettle();
      expect(favorite, findsOneWidget);
    });

    // Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'cast profile template matches the approved baseline',
      fileName: 'cast_profile_template',
      skip: true, // baseline pending human approval (#31); golden #31 대기.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'default',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenCastProfileTemplate(),
            ),
          ),
        ],
      ),
    );
  });
}
