// Smoke test for the atom catalogue. Renders the whole gallery under the Assen
// theme and asserts atoms across the (lazily built) list paint without error by
// scrolling through them — the widget-test equivalent of the `flutter build
// web` smoke check.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  testWidgets('AtomCatalog renders top-of-list atoms without error', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: AssenTheme.light(), home: const AtomCatalog()),
    );
    await tester.pump();

    // The app bar plus the first viewport's atoms prove the gallery built.
    expect(find.text('Atoms'), findsOneWidget);
    expect(find.byType(AssenButton), findsWidgets);
    expect(find.byType(AssenFavoriteButton), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('AtomCatalog builds its later sections when scrolled', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: AssenTheme.light(), home: const AtomCatalog()),
    );
    await tester.pump();

    // The donut/card live below the fold in the lazy ListView; scrolling builds
    // them. scrollUntilVisible drives the list and proves they render cleanly.
    await tester.scrollUntilVisible(
      find.byType(AssenProgressDonut),
      300,
      scrollable: find.byType(Scrollable),
    );
    expect(find.byType(AssenProgressDonut), findsOneWidget);

    // Card is the last section; scrolling to the Card text builds it. The
    // finder must not use `.first` (it would throw before the widget exists).
    await tester.scrollUntilVisible(
      find.text('level0 — 보더'),
      300,
      scrollable: find.byType(Scrollable),
    );
    expect(find.byType(AssenCard), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('catalog favourite toggle responds to interaction', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: AssenTheme.light(), home: const AtomCatalog()),
    );
    await tester.pump();

    // The favourite button starts on (filled heart); tapping flips it to the
    // outline state, proving the gallery wiring is live.
    expect(find.byIcon(Icons.favorite), findsOneWidget);
    await tester.tap(find.byType(AssenFavoriteButton));
    await tester.pump();
    expect(find.byIcon(Icons.favorite_border), findsOneWidget);
  });
}
