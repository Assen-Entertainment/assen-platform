// Smoke test for the MoleculeCatalog review surface (ASS-88). Rendering the
// whole gallery under the Assen theme exercises every molecule at once — the
// lightweight stand-in for the `flutter build web` catalogue smoke on WSL2.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  testWidgets('MoleculeCatalog renders every molecule without error', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AssenTheme.light(),
        home: const MoleculeCatalog(),
      ),
    );
    // The app bar title plus a leading section title confirm the gallery built
    // and laid out without throwing (no overflow/paint exception).
    expect(find.text('Molecules'), findsOneWidget);
    expect(find.textContaining('TextField'), findsWidgets);

    // Scroll the outer ListView so the lazily-built lower sections (banner,
    // stat cards) also mount and paint at least once.
    await tester.dragUntilVisible(
      find.textContaining('StatCard'),
      find.byType(Scrollable).first,
      const Offset(0, -400),
    );
    expect(find.textContaining('StatCard'), findsOneWidget);
  });
}
