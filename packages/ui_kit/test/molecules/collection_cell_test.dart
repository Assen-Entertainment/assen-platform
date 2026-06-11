// Widget tests for AssenCollectionCell (획득 / 미획득(실루엣+잠금) / NEW). Owned cells
// show the label; locked cells hide it behind a lock. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 120, child: child)),
  ),
);

void main() {
  group('AssenCollectionCell', () {
    testWidgets('shows the label when owned', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCollectionCell(
            artwork: ColoredBox(color: Color(0xFFCFE9F2)),
            label: '봄 체키',
          ),
        ),
      );
      expect(find.text('봄 체키'), findsOneWidget);
    });

    testWidgets('hides label and locks when not owned', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCollectionCell(
            artwork: ColoredBox(color: Color(0xFFCFE9F2)),
            label: '여름 체키',
            state: AssenCollectionState.locked,
          ),
        ),
      );
      expect(find.text('여름 체키'), findsNothing);
      expect(find.text('???'), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline), findsOneWidget);
    });

    testWidgets('renders a NEW badge when given', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCollectionCell(
            artwork: ColoredBox(color: Color(0xFFCFE9F2)),
            label: '봄 체키',
            badge: AssenBadge(label: 'NEW'),
          ),
        ),
      );
      expect(find.text('NEW'), findsOneWidget);
    });
  });

  goldenTest(
    'collection cell matches the approved baseline',
    fileName: 'collection_cell',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'locked',
          child: const SizedBox(
            width: 120,
            child: AssenCollectionCell(
              artwork: ColoredBox(color: Color(0xFFCFE9F2)),
              label: '여름 체키',
              state: AssenCollectionState.locked,
            ),
          ),
        ),
      ],
    ),
  );
}
