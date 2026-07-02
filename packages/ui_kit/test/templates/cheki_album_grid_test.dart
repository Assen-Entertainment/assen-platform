import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void _setLogicalSize(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 1200);
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
  group('assenGridCrossAxisCount', () {
    test('maps width to the per-class column count', () {
      expect(
        assenGridCrossAxisCount(390, compact: 3, medium: 4, expanded: 5),
        3,
      );
      expect(
        assenGridCrossAxisCount(700, compact: 3, medium: 4, expanded: 5),
        4,
      );
      expect(
        assenGridCrossAxisCount(1000, compact: 3, medium: 4, expanded: 5),
        5,
      );
    });

    test('uses the M3 boundaries (600 medium, 840 expanded, inclusive)', () {
      expect(
        assenGridCrossAxisCount(599, compact: 1, medium: 2, expanded: 3),
        1,
      );
      expect(
        assenGridCrossAxisCount(600, compact: 1, medium: 2, expanded: 3),
        2,
      );
      expect(
        assenGridCrossAxisCount(839, compact: 1, medium: 2, expanded: 3),
        2,
      );
      expect(
        assenGridCrossAxisCount(840, compact: 1, medium: 2, expanded: 3),
        3,
      );
    });
  });

  group('AssenChekiAlbumTemplate responsive grid', () {
    testWidgets('keeps the 3-up grid at mobile width', (tester) async {
      _setLogicalSize(tester, 390);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(),
        ),
      );

      expect(_albumColumns(tester), 3);
    });

    testWidgets('uses 4 columns at tablet/medium width', (tester) async {
      _setLogicalSize(tester, 768);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(),
        ),
      );

      expect(_albumColumns(tester), 4);
    });

    testWidgets('densifies to 5 columns at desktop width', (tester) async {
      _setLogicalSize(tester, 1280);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenChekiAlbumTemplate(),
        ),
      );

      expect(_albumColumns(tester), 5);
    });

    testWidgets('stays 5 columns at the shell-clamped desktop column (1280)', (
      tester,
    ) async {
      // fan_app renders this template inside ASS-141's adaptive shell, which
      // clamps content to AssenLayout.contentMaxWidth (1280). Pin the real
      // integrated geometry, not just the unclamped viewport: 1280 is still in
      // the expanded class, so the gallery is 5-up.
      _setLogicalSize(tester, 1280);

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const Center(
            child: SizedBox(
              width: AssenLayout.contentMaxWidth,
              height: 1100,
              child: AssenChekiAlbumTemplate(),
            ),
          ),
        ),
      );

      expect(_albumColumns(tester), 5);
    });
  });
}
