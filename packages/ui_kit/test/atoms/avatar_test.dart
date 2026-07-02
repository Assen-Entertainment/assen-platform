// Widget tests for AssenAvatar. Pixel golden skipped pending #31.

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
  group('AssenAvatar', () {
    testWidgets('falls back to the first initial when no image', (
      tester,
    ) async {
      await tester.pumpWidget(_host(const AssenAvatar(name: '하나')));
      expect(find.text('하'), findsOneWidget);
    });

    testWidgets('size L is larger than size S', (tester) async {
      await tester.pumpWidget(
        _host(
          const Row(
            children: [
              AssenAvatar(name: 'a', size: AssenAvatarSize.s),
              AssenAvatar(name: 'b', size: AssenAvatarSize.l),
            ],
          ),
        ),
      );
      final small = tester.getSize(find.byType(AssenAvatar).first);
      final large = tester.getSize(find.byType(AssenAvatar).last);
      expect(large.width, greaterThan(small.width));
    });

    testWidgets('hue tints the fallback surface', (tester) async {
      await tester.pumpWidget(
        _host(const AssenAvatar(name: '미오', hue: AssenBadgeHue.sky)),
      );
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(AssenAvatar),
              matching: find.byType(Container),
            )
            .first,
      );
      final decoration = container.decoration! as BoxDecoration;
      expect(decoration.color, RefColors.skyBg);
    });

    testWidgets('online dot appears only when isOnline', (tester) async {
      await tester.pumpWidget(
        _host(const AssenAvatar(name: '리코', isOnline: true)),
      );
      // The dot overlay introduces a Stack inside the avatar subtree.
      final stackInside = find.descendant(
        of: find.byType(AssenAvatar),
        matching: find.byType(Stack),
      );
      expect(stackInside, findsOneWidget);
    });

    testWidgets('no online dot when offline', (tester) async {
      await tester.pumpWidget(_host(const AssenAvatar(name: '리코')));
      final stackInside = find.descendant(
        of: find.byType(AssenAvatar),
        matching: find.byType(Stack),
      );
      expect(stackInside, findsNothing);
    });
  });

  goldenTest(
    'AssenAvatar matches the approved baseline',
    fileName: 'avatar',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'initial-fallback',
          child: const AssenAvatar(name: '하나', hue: AssenBadgeHue.strawberry),
        ),
        GoldenTestScenario(
          name: 'online-large',
          child: const AssenAvatar(
            name: '리코',
            size: AssenAvatarSize.l,
            hue: AssenBadgeHue.lavender,
            isOnline: true,
          ),
        ),
      ],
    ),
  );
}
