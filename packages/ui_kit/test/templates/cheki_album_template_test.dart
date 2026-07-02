// Smoke + structure test for the T4 cheki album template (ASS-88), covering
// both the filled and empty variants. The pixel golden is declared but skipped
// (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenChekiAlbumTemplate', () {
    testWidgets('filled variant renders the progress count and frame grid', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(),
        ),
      );

      expect(find.text('체키 앨범'), findsOneWidget);
      // The 도감 count reads the 6/12 placeholder over a progress bar.
      expect(find.text('6 / 12'), findsOneWidget);
      expect(find.byType(AssenProgressBar), findsOneWidget);
      // Six owned cheki frames render as the album cells.
      expect(find.byType(AssenChekiFrame), findsNWidgets(6));
      // The locked silhouettes trail the owned frames.
      expect(find.byType(AssenCollectionCell), findsNWidgets(3));
      // The filled variant does NOT show the empty state.
      expect(find.byType(AssenEmptyState), findsNothing);
    });

    testWidgets('empty variant swaps the grid for the empty state', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(
            variant: AssenChekiAlbumVariant.empty,
          ),
        ),
      );

      // The empty state replaces the grid; no frames are shown.
      expect(find.byType(AssenEmptyState), findsOneWidget);
      expect(find.byType(AssenChekiFrame), findsNothing);
      // The 도감 count zeroes out in the empty variant.
      expect(find.text('0 / 12'), findsOneWidget);
      expect(find.text('캐스트 보러 가기'), findsOneWidget);
    });

    // Real pixel golden — declared but deferred to human approval (#31).
    goldenTest(
      'cheki album template matches the approved baseline',
      fileName: 'cheki_album_template',
      skip: true, // baseline pending human approval (#31); golden #31 대기.
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'filled',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenChekiAlbumTemplate(),
            ),
          ),
          GoldenTestScenario(
            name: 'empty',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenChekiAlbumTemplate(
                variant: AssenChekiAlbumVariant.empty,
              ),
            ),
          ),
        ],
      ),
    );
  });
}
