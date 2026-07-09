// Widget tests for AssenMembershipCard (간판 컴포넌트). Identity fields, skin
// surface mapping, and the QR entry affordance. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 340, child: child)),
  ),
);

Color _surfaceOf(WidgetTester tester) {
  final container = tester.widget<Container>(
    find
        .descendant(
          of: find.byType(AssenMembershipCard),
          matching: find.byType(Container),
        )
        .first,
  );
  return (container.decoration! as BoxDecoration).color!;
}

void main() {
  group('AssenMembershipCard', () {
    testWidgets('renders name, number, points and tier', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenMembershipCard(
            name: '미오',
            memberNumber: '0000 1234 5678',
            points: '1,280',
            tierLabel: '하츠코이',
            avatar: AssenAvatar(name: '미오', hue: AssenBadgeHue.strawberry),
          ),
        ),
      );
      expect(find.text('미오'), findsOneWidget);
      expect(find.text('0000 1234 5678'), findsOneWidget);
      expect(find.text('1,280'), findsOneWidget);
      expect(find.text('하츠코이'), findsOneWidget);
    });

    testWidgets('strawberry skin fills with the strawberry surface', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenMembershipCard(
            name: '미오',
            memberNumber: '0000',
            points: '0',
            tierLabel: '하츠코이',
            avatar: AssenAvatar(name: '미오'),
          ),
        ),
      );
      expect(_surfaceOf(tester), RefColors.pinkBg);
    });

    testWidgets('sky skin fills with the sky surface', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenMembershipCard(
            name: '유키',
            memberNumber: '0000',
            points: '0',
            tierLabel: '하츠코이',
            skin: AssenMembershipSkin.sky,
            avatar: AssenAvatar(name: '유키'),
          ),
        ),
      );
      expect(_surfaceOf(tester), RefColors.skyBg);
    });

    testWidgets('shows the QR button only when onShowQr is set', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenMembershipCard(
            name: '미오',
            memberNumber: '0000',
            points: '0',
            tierLabel: '하츠코이',
            avatar: AssenAvatar(name: '미오'),
          ),
        ),
      );
      expect(find.byIcon(Icons.qr_code_2), findsNothing);

      var qr = 0;
      await tester.pumpWidget(
        _host(
          AssenMembershipCard(
            name: '미오',
            memberNumber: '0000',
            points: '0',
            tierLabel: '하츠코이',
            avatar: const AssenAvatar(name: '미오'),
            onShowQr: () => qr++,
          ),
        ),
      );
      expect(find.byIcon(Icons.qr_code_2), findsOneWidget);
      await tester.tap(find.byIcon(Icons.qr_code_2));
      expect(qr, 1);
    });
  });

  goldenTest(
    'membership card matches the approved baseline',
    fileName: 'membership_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'strawberry',
          child: SizedBox(
            width: 340,
            child: AssenMembershipCard(
              name: '미오',
              memberNumber: '0000 1234 5678',
              points: '1,280',
              tierLabel: '하츠코이',
              avatar: const AssenAvatar(
                name: '미오',
                hue: AssenBadgeHue.strawberry,
              ),
              onShowQr: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
