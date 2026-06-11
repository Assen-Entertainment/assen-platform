// Widget tests for AssenAppBar + AssenTabBar (Navigation organisms). Centre
// title, back affordance, five-tab selection, badge overlay. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) =>
    MaterialApp(theme: AssenTheme.light(), home: child);

const _tabs = [
  AssenTabItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: '홈'),
  AssenTabItem(icon: Icons.calendar_month_outlined, label: '출근표'),
  AssenTabItem(icon: Icons.event_outlined, label: '예약'),
  AssenTabItem(icon: Icons.photo_library_outlined, label: '체키', badgeCount: 3),
  AssenTabItem(icon: Icons.person_outline, label: '마이'),
];

void main() {
  group('AssenAppBar', () {
    testWidgets('renders the centred title', (tester) async {
      await tester.pumpWidget(
        _host(const Scaffold(appBar: AssenAppBar(title: '예약'))),
      );
      expect(find.text('예약'), findsOneWidget);
    });

    testWidgets('shows a back button only when onBack is set', (tester) async {
      await tester.pumpWidget(
        _host(const Scaffold(appBar: AssenAppBar(title: '루트'))),
      );
      expect(find.byIcon(Icons.arrow_back_ios_new), findsNothing);

      var backs = 0;
      await tester.pumpWidget(
        _host(
          Scaffold(
            appBar: AssenAppBar(title: '상세', onBack: () => backs++),
          ),
        ),
      );
      expect(find.byIcon(Icons.arrow_back_ios_new), findsOneWidget);
      await tester.tap(find.byIcon(Icons.arrow_back_ios_new));
      expect(backs, 1);
    });

    testWidgets('renders trailing actions', (tester) async {
      await tester.pumpWidget(
        _host(
          Scaffold(
            appBar: AssenAppBar(
              title: '홈',
              actions: [
                AssenIconButton(
                  icon: Icons.notifications_none,
                  semanticLabel: '알림',
                  onPressed: () {},
                ),
              ],
            ),
          ),
        ),
      );
      expect(find.byIcon(Icons.notifications_none), findsOneWidget);
    });
  });

  group('AssenTabBar', () {
    testWidgets('renders every destination label', (tester) async {
      await tester.pumpWidget(
        _host(
          Scaffold(
            bottomNavigationBar: AssenTabBar(
              items: _tabs,
              currentIndex: 0,
              onChanged: (_) {},
            ),
          ),
        ),
      );
      for (final label in ['홈', '출근표', '예약', '체키', '마이']) {
        expect(find.text(label), findsOneWidget);
      }
    });

    testWidgets('reports the tapped index', (tester) async {
      var tapped = -1;
      await tester.pumpWidget(
        _host(
          Scaffold(
            bottomNavigationBar: AssenTabBar(
              items: _tabs,
              currentIndex: 0,
              onChanged: (i) => tapped = i,
            ),
          ),
        ),
      );
      await tester.tap(find.text('예약'));
      expect(tapped, 2);
    });

    testWidgets('overlays a count badge on a tab', (tester) async {
      await tester.pumpWidget(
        _host(
          Scaffold(
            bottomNavigationBar: AssenTabBar(
              items: _tabs,
              currentIndex: 0,
              onChanged: (_) {},
            ),
          ),
        ),
      );
      // The 체키 tab carries badgeCount: 3 — shown via AssenCountBadge.
      expect(find.text('3'), findsOneWidget);
      expect(find.byType(AssenCountBadge), findsOneWidget);
    });
  });

  goldenTest(
    'app bar and tab bar match the approved baseline',
    fileName: 'app_bar',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'app-bar',
          child: const SizedBox(
            width: 360,
            child: AssenAppBar(title: '예약'),
          ),
        ),
      ],
    ),
  );
}
