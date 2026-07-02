// Widget tests for AssenListItem (leading / title / subtitle / trailing slots).
// Auto chevron appears for tappable rows without a trailing slot. Golden #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenListItem', () {
    testWidgets('renders title and subtitle', (tester) async {
      await tester.pumpWidget(
        _host(const AssenListItem(title: '내 회원증', subtitle: '하츠코이 본점')),
      );
      expect(find.text('내 회원증'), findsOneWidget);
      expect(find.text('하츠코이 본점'), findsOneWidget);
    });

    testWidgets('fires onTap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _host(AssenListItem(title: '설정', onTap: () => tapped = true)),
      );
      await tester.tap(find.text('설정'));
      expect(tapped, isTrue);
    });

    testWidgets('shows the auto chevron for a tappable row', (tester) async {
      await tester.pumpWidget(
        _host(AssenListItem(title: '설정', onTap: () {})),
      );
      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
    });

    testWidgets('a trailing slot suppresses the auto chevron', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenListItem(
            title: '알림',
            trailing: const Icon(Icons.circle),
            onTap: () {},
          ),
        ),
      );
      expect(find.byIcon(Icons.chevron_right), findsNothing);
    });
  });

  goldenTest(
    'list item matches the approved baseline',
    fileName: 'list_item',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-subtitle',
          child: const SizedBox(
            width: 320,
            child: AssenListItem(title: '내 회원증', subtitle: '하츠코이 본점'),
          ),
        ),
      ],
    ),
  );
}
