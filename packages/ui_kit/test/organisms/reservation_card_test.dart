// Widget tests for AssenReservationCard. Status badge per state, the D-day chip
// and actions on upcoming only, and the detail rows. Golden skip #31.

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
  group('AssenReservationCard', () {
    testWidgets('renders venue, detail rows and the confirmed badge', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenReservationCard(
            venue: '하츠코이 본점',
            dateTime: '6월 14일 (토) 14:00',
            partySize: '2명',
            status: AssenReservationStatus.upcoming,
          ),
        ),
      );
      expect(find.text('하츠코이 본점'), findsOneWidget);
      expect(find.text('6월 14일 (토) 14:00'), findsOneWidget);
      expect(find.text('2명'), findsOneWidget);
      expect(find.text('예약 확정'), findsOneWidget);
    });

    testWidgets('upcoming shows the D-day chip and actions', (tester) async {
      var prim = 0;
      var sec = 0;
      await tester.pumpWidget(
        _host(
          AssenReservationCard(
            venue: '하츠코이 본점',
            dateTime: '6월 14일 (토) 14:00',
            partySize: '2명',
            status: AssenReservationStatus.upcoming,
            ddayLabel: 'D-2',
            primaryLabel: '예약 변경',
            onPrimary: () => prim++,
            secondaryLabel: '취소',
            onSecondary: () => sec++,
          ),
        ),
      );
      expect(find.text('D-2'), findsOneWidget);
      await tester.tap(find.text('예약 변경'));
      await tester.tap(find.text('취소'));
      expect(prim, 1);
      expect(sec, 1);
    });

    testWidgets('visited maps to the done badge and hides actions', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const AssenReservationCard(
            venue: '하츠코이 본점',
            dateTime: '5월 28일 (수) 19:00',
            partySize: '1명',
            status: AssenReservationStatus.visited,
            ddayLabel: 'D-2',
            primaryLabel: '예약 변경',
          ),
        ),
      );
      expect(find.text('방문 완료'), findsOneWidget);
      // D-day and actions are upcoming-only.
      expect(find.text('D-2'), findsNothing);
      expect(find.text('예약 변경'), findsNothing);
    });

    testWidgets('cancelled maps to the cancelled badge', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenReservationCard(
            venue: '하츠코이 2호점',
            dateTime: '5월 20일 (화) 13:00',
            partySize: '3명',
            status: AssenReservationStatus.cancelled,
          ),
        ),
      );
      expect(find.text('취소됨'), findsOneWidget);
    });
  });

  goldenTest(
    'reservation card matches the approved baseline',
    fileName: 'reservation_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'upcoming',
          child: SizedBox(
            width: 360,
            child: AssenReservationCard(
              venue: '하츠코이 본점',
              dateTime: '6월 14일 (토) 14:00',
              partySize: '2명',
              status: AssenReservationStatus.upcoming,
              ddayLabel: 'D-2',
              primaryLabel: '예약 변경',
              onPrimary: () {},
              secondaryLabel: '취소',
              onSecondary: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
