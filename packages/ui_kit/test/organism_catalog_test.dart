// Smoke test for the OrganismCatalog review surface (ASS-88). Rendering the
// whole gallery under the Assen theme exercises every organism at once — the
// lightweight stand-in for the `flutter build web` catalogue smoke on WSL2.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  testWidgets('OrganismCatalog renders every organism without error', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AssenTheme.light(),
        home: const OrganismCatalog(),
      ),
    );
    // The app bar title plus a leading section title confirm the gallery built
    // and laid out without throwing (no overflow/paint exception).
    expect(find.text('Organisms'), findsOneWidget);
    expect(find.textContaining('MembershipCard'), findsOneWidget);

    // Scroll the outer ListView so the lazily-built lower sections (states,
    // report list, bottom CTA) also mount and paint at least once.
    await tester.dragUntilVisible(
      find.textContaining('BottomCTA'),
      find.byType(Scrollable).first,
      const Offset(0, -600),
    );
    expect(find.textContaining('BottomCTA'), findsOneWidget);
  });
}
