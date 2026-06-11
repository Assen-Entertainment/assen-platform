// Widget tests for AssenScheduleCalendar. Week strip, day selection, the cast
// list for the selected day, and the closed/empty rows. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: SizedBox(width: 380, child: child),
  ),
);

const _week = [
  AssenScheduleDay(
    weekday: '월',
    day: 9,
    casts: [
      AssenScheduleCast(
        name: '미오',
        shift: '12:00–18:00',
        hue: AssenBadgeHue.strawberry,
      ),
    ],
  ),
  AssenScheduleDay(weekday: '화', day: 10, isClosed: true),
  AssenScheduleDay(
    weekday: '수',
    day: 11,
    hasEvent: true,
    casts: [
      AssenScheduleCast(
        name: '유키',
        shift: '13:00–19:00',
        hue: AssenBadgeHue.sky,
      ),
    ],
  ),
];

void main() {
  group('AssenScheduleCalendar', () {
    testWidgets('renders the week strip days', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenScheduleCalendar(
            days: _week,
            selectedIndex: 0,
            onSelect: (_) {},
          ),
        ),
      );
      expect(find.text('월'), findsOneWidget);
      expect(find.text('화'), findsOneWidget);
      expect(find.text('수'), findsOneWidget);
    });

    testWidgets('lists the selected day cast and shift', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenScheduleCalendar(
            days: _week,
            selectedIndex: 0,
            onSelect: (_) {},
          ),
        ),
      );
      expect(find.text('미오'), findsOneWidget);
      expect(find.text('12:00–18:00'), findsOneWidget);
    });

    testWidgets('reports a tapped day', (tester) async {
      var selected = -1;
      await tester.pumpWidget(
        _host(
          AssenScheduleCalendar(
            days: _week,
            selectedIndex: 0,
            onSelect: (i) => selected = i,
          ),
        ),
      );
      await tester.tap(find.text('수'));
      expect(selected, 2);
    });

    testWidgets('shows the closed row for a 휴무 day', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenScheduleCalendar(
            days: _week,
            selectedIndex: 1,
            onSelect: (_) {},
          ),
        ),
      );
      expect(find.text('휴무일이에요'), findsOneWidget);
    });
  });

  goldenTest(
    'schedule calendar matches the approved baseline',
    fileName: 'schedule_calendar',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'selected',
          child: SizedBox(
            width: 380,
            child: AssenScheduleCalendar(
              days: _week,
              selectedIndex: 0,
              todayIndex: 2,
              onSelect: (_) {},
            ),
          ),
        ),
      ],
    ),
  );
}
