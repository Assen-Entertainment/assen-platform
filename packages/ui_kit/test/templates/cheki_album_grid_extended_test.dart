import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the wide (large/extra-large) cheki album grid (ASS-147 Slice 3): at the
/// QHD desktop width the gallery densifies to >= 5 columns so it fills the
/// widened sidebar-shell body instead of leaving a sparse column. The existing
/// cheki_album_grid_test.dart keeps covering the mobile/tablet/expanded counts
/// (3/4/5) and is not edited.
void _setLogicalSize(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 1600);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

int _albumColumns(WidgetTester tester) {
  final grid = tester.widget<GridView>(find.byType(GridView));
  final delegate =
      grid.gridDelegate as SliverGridDelegateWithFixedCrossAxisCount;
  return delegate.crossAxisCount;
}

void main() {
  group('AssenChekiAlbumTemplate wide grid (ASS-147 Slice 3)', () {
    testWidgets('resolves >= 5 columns at the QHD desktop width (2560)', (
      tester,
    ) async {
      _setLogicalSize(tester, 2560);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(),
        ),
      );

      // 2560 (minus screen margins) is the extra-large class -> 6 frames a row.
      expect(_albumColumns(tester), greaterThanOrEqualTo(5));
    });

    testWidgets('counts from the LOCAL grid width, not the window', (
      tester,
    ) async {
      // The cheki tab renders inside the desktop sidebar shell, whose 256dp
      // sidebar shrinks the body below the window. Emulate that by constraining
      // the template to a 1300dp body inside a 2560 window: the window is the
      // extra-large class (would be 6 columns), but the body is the large
      // class. Asserting 5 (not 6) proves the count reads constraints.maxWidth
      // of the local grid, never the raw 2560 window.
      _setLogicalSize(tester, 2560);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const Center(
            child: SizedBox(
              width: 1300,
              height: 1400,
              child: AssenChekiAlbumTemplate(),
            ),
          ),
        ),
      );

      expect(_albumColumns(tester), 5);
    });
  });
}
