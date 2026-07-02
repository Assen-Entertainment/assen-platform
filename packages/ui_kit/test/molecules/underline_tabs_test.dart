// Widget tests for AssenUnderlineTabs (selected / unselected). Horizontally
// scrollable; reports the tapped index. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenUnderlineTabs', () {
    testWidgets('renders the tabs', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenUnderlineTabs(
            tabs: const ['전체', '체키', '이벤트'],
            selectedIndex: 0,
            onChanged: (_) {},
          ),
        ),
      );
      expect(find.text('체키'), findsOneWidget);
    });

    testWidgets('reports the tapped index', (tester) async {
      int? index;
      await tester.pumpWidget(
        _host(
          AssenUnderlineTabs(
            tabs: const ['전체', '체키', '이벤트'],
            selectedIndex: 0,
            onChanged: (i) => index = i,
          ),
        ),
      );
      await tester.tap(find.text('이벤트'));
      expect(index, 2);
    });
  });

  goldenTest(
    'underline tabs match the approved baseline',
    fileName: 'underline_tabs',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'second-selected',
          child: SizedBox(
            width: 320,
            child: AssenUnderlineTabs(
              tabs: const ['전체', '체키', '이벤트'],
              selectedIndex: 1,
              onChanged: (_) {},
            ),
          ),
        ),
      ],
    ),
  );
}
