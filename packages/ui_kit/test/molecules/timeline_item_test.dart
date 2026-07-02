// Widget tests for AssenTimelineItem (날짜 그룹 + 항목). Renders date/title/subtitle
// and an optional trailing slot. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenTimelineItem', () {
    testWidgets('renders date, title and subtitle', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenTimelineItem(
            date: '2026.06.10',
            title: '12번째 방문',
            subtitle: '만난 캐스트: 미오',
          ),
        ),
      );
      expect(find.text('2026.06.10'), findsOneWidget);
      expect(find.text('12번째 방문'), findsOneWidget);
      expect(find.text('만난 캐스트: 미오'), findsOneWidget);
    });

    testWidgets('renders the trailing slot', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenTimelineItem(
            date: '2026.06.10',
            title: '포인트 적립',
            trailing: Text('+120 P'),
          ),
        ),
      );
      expect(find.text('+120 P'), findsOneWidget);
    });
  });

  goldenTest(
    'timeline item matches the approved baseline',
    fileName: 'timeline_item',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'visit',
          child: const SizedBox(
            width: 320,
            child: AssenTimelineItem(
              date: '2026.06.10',
              title: '12번째 방문',
              subtitle: '만난 캐스트: 미오, 리코',
              isFirst: true,
            ),
          ),
        ),
      ],
    ),
  );
}
