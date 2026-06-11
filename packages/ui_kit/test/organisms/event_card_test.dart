// Widget tests for AssenEventCard. Poster slot, status per state, D-day badge,
// cast stack, and CTA visibility (hidden when ended). Golden skip #31.

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
  group('AssenEventCard', () {
    testWidgets('renders title, period and the upcoming status', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenEventCard(
            title: '6월 콜라보 이벤트',
            period: '6.10 – 6.30',
            status: AssenEventStatus.upcoming,
            slot: ColoredBox(color: Color(0xFFEEEEEE)),
          ),
        ),
      );
      expect(find.text('6월 콜라보 이벤트'), findsOneWidget);
      expect(find.text('6.10 – 6.30'), findsOneWidget);
      expect(find.text('예정'), findsOneWidget);
    });

    testWidgets('upcoming shows the D-day badge and fires the CTA', (
      tester,
    ) async {
      var cta = 0;
      await tester.pumpWidget(
        _host(
          AssenEventCard(
            title: '콜라보',
            period: '6.10 – 6.30',
            status: AssenEventStatus.upcoming,
            slot: const ColoredBox(color: Color(0xFFEEEEEE)),
            ddayLabel: 'D-5',
            ctaLabel: '예약하기',
            onCta: () => cta++,
          ),
        ),
      );
      expect(find.text('D-5'), findsOneWidget);
      await tester.tap(find.text('예약하기'));
      expect(cta, 1);
    });

    testWidgets('ended hides the D-day and the CTA', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenEventCard(
            title: '봄 한정',
            period: '4.1 – 4.30',
            status: AssenEventStatus.ended,
            slot: ColoredBox(color: Color(0xFFEEEEEE)),
            ddayLabel: 'D-5',
            ctaLabel: '예약하기',
          ),
        ),
      );
      expect(find.text('종료'), findsOneWidget);
      expect(find.text('D-5'), findsNothing);
      expect(find.text('예약하기'), findsNothing);
    });

    testWidgets('renders the featured cast avatars', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenEventCard(
            title: '콜라보',
            period: '6.10 – 6.30',
            status: AssenEventStatus.ongoing,
            slot: ColoredBox(color: Color(0xFFEEEEEE)),
            casts: [
              AssenScheduleCastRef(name: '미오', hue: AssenBadgeHue.strawberry),
              AssenScheduleCastRef(name: '유키', hue: AssenBadgeHue.sky),
            ],
          ),
        ),
      );
      expect(find.byType(AssenAvatar), findsNWidgets(2));
    });
  });

  goldenTest(
    'event card matches the approved baseline',
    fileName: 'event_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'upcoming',
          child: SizedBox(
            width: 360,
            child: AssenEventCard(
              title: '6월 콜라보 이벤트',
              period: '6.10 – 6.30',
              status: AssenEventStatus.upcoming,
              slot: const ColoredBox(color: Color(0xFFE2DAF4)),
              ddayLabel: 'D-5',
              casts: const [
                AssenScheduleCastRef(name: '미오', hue: AssenBadgeHue.strawberry),
              ],
              ctaLabel: '예약하기',
              onCta: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
