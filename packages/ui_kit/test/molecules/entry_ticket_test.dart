// Widget tests for AssenEntryTicket (대기중 / 호출됨 / 입장완료). Renders the queue
// title + number and a state-specific caption. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 200, child: child)),
  ),
);

void main() {
  group('AssenEntryTicket', () {
    testWidgets('renders title and number', (tester) async {
      await tester.pumpWidget(
        _host(const AssenEntryTicket(title: '하츠코이 본점', number: 'A-23')),
      );
      expect(find.text('하츠코이 본점'), findsOneWidget);
      expect(find.text('A-23'), findsOneWidget);
    });

    testWidgets('waiting shows the 대기중 caption', (tester) async {
      await tester.pumpWidget(
        _host(const AssenEntryTicket(title: '본점', number: 'A-23')),
      );
      expect(find.text('대기중'), findsOneWidget);
    });

    testWidgets('called shows the come-in caption', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenEntryTicket(
            title: '본점',
            number: 'A-23',
            state: AssenEntryState.called,
          ),
        ),
      );
      expect(find.text('입장해 주세요'), findsOneWidget);
    });
  });

  goldenTest(
    'entry ticket matches the approved baseline',
    fileName: 'entry_ticket',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'called',
          child: const SizedBox(
            width: 200,
            child: AssenEntryTicket(
              title: '하츠코이 본점',
              number: 'A-23',
              state: AssenEntryState.called,
            ),
          ),
        ),
      ],
    ),
  );
}
