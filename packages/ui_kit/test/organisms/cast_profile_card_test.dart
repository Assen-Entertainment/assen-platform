// Widget tests for AssenCastProfileCard. Name + tagline, 출근중 badge, the 최애
// favourite toggle, and the tap. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 360, child: child)),
  ),
);

void main() {
  group('AssenCastProfileCard', () {
    testWidgets('renders name and tagline', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenCastProfileCard(
            name: '모카',
            hue: AssenBadgeHue.peach,
            tagline: '달콤한 디저트 담당',
            isFavorite: false,
            onFavoriteChanged: (_) {},
          ),
        ),
      );
      expect(find.text('모카'), findsOneWidget);
      expect(find.text('달콤한 디저트 담당'), findsOneWidget);
    });

    testWidgets('shows the 출근중 badge only when on shift', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenCastProfileCard(
            name: '베리',
            hue: AssenBadgeHue.lavender,
            isFavorite: false,
            onFavoriteChanged: (_) {},
          ),
        ),
      );
      expect(find.text('출근중'), findsNothing);

      await tester.pumpWidget(
        _host(
          AssenCastProfileCard(
            name: '모카',
            hue: AssenBadgeHue.peach,
            isOnShift: true,
            isFavorite: false,
            onFavoriteChanged: (_) {},
          ),
        ),
      );
      expect(find.text('출근중'), findsOneWidget);
    });

    testWidgets('toggles 최애 via the favourite button', (tester) async {
      bool? changed;
      await tester.pumpWidget(
        _host(
          AssenCastProfileCard(
            name: '모카',
            hue: AssenBadgeHue.peach,
            isFavorite: false,
            onFavoriteChanged: (v) => changed = v,
          ),
        ),
      );
      await tester.tap(find.byType(AssenFavoriteButton));
      expect(changed, isTrue);
    });

    testWidgets('fires onTap', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenCastProfileCard(
            name: '모카',
            hue: AssenBadgeHue.peach,
            isFavorite: false,
            onFavoriteChanged: (_) {},
            onTap: () => taps++,
          ),
        ),
      );
      await tester.tap(find.text('모카'));
      expect(taps, 1);
    });
  });

  goldenTest(
    'cast profile card matches the approved baseline',
    fileName: 'cast_profile_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'on-shift-favourite',
          child: SizedBox(
            width: 360,
            child: AssenCastProfileCard(
              name: '모카',
              hue: AssenBadgeHue.peach,
              tagline: '달콤한 디저트 담당',
              isOnShift: true,
              isFavorite: true,
              onFavoriteChanged: (_) {},
            ),
          ),
        ),
      ],
    ),
  );
}
