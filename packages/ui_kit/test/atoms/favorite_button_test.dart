// Widget tests for AssenFavoriteButton. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenFavoriteButton', () {
    testWidgets('shows a filled heart when favourite', (tester) async {
      await tester.pumpWidget(
        _host(AssenFavoriteButton(isFavorite: true, onChanged: (_) {})),
      );
      expect(find.byIcon(Icons.favorite), findsOneWidget);
      expect(find.byIcon(Icons.favorite_border), findsNothing);
    });

    testWidgets('shows an outline heart when not favourite', (tester) async {
      await tester.pumpWidget(
        _host(AssenFavoriteButton(isFavorite: false, onChanged: (_) {})),
      );
      expect(find.byIcon(Icons.favorite_border), findsOneWidget);
    });

    testWidgets('favourite heart uses the rose anchor colour', (tester) async {
      await tester.pumpWidget(
        _host(AssenFavoriteButton(isFavorite: true, onChanged: (_) {})),
      );
      // The colour is applied on the IconButton (resolved into the glyph via
      // IconTheme), so assert it there rather than on the Icon widget.
      final button = tester.widget<IconButton>(find.byType(IconButton));
      expect(button.color, RefColors.roseMain);
    });

    testWidgets('toggles to the opposite value on tap', (tester) async {
      bool? next;
      await tester.pumpWidget(
        _host(
          AssenFavoriteButton(isFavorite: false, onChanged: (v) => next = v),
        ),
      );
      await tester.tap(find.byType(AssenFavoriteButton));
      expect(next, isTrue);
    });

    testWidgets('disabled when onChanged is null', (tester) async {
      await tester.pumpWidget(
        _host(const AssenFavoriteButton(isFavorite: false, onChanged: null)),
      );
      final button = tester.widget<IconButton>(find.byType(IconButton));
      expect(button.onPressed, isNull);
    });
  });

  goldenTest(
    'AssenFavoriteButton matches the approved baseline',
    fileName: 'favorite_button',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'on',
          child: AssenFavoriteButton(isFavorite: true, onChanged: (_) {}),
        ),
        GoldenTestScenario(
          name: 'off',
          child: AssenFavoriteButton(isFavorite: false, onChanged: (_) {}),
        ),
      ],
    ),
  );
}
