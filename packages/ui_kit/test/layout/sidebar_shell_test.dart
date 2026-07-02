import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

const _items = [
  AssenTabItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: '홈'),
  AssenTabItem(
    icon: Icons.photo_library_outlined,
    label: '체키',
    badgeCount: 3,
  ),
  AssenTabItem(icon: Icons.person_outline, label: '마이'),
];

Widget _host() => MaterialApp(
  theme: AssenTheme.light(),
  home: AssenSidebarShell(
    currentIndex: 0,
    onChanged: _noop,
    items: _items,
    header: const Text('하츠코이'),
    body: const SizedBox.expand(key: Key('shell-body')),
  ),
);

void _noop(int _) {}

void _setWidth(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 900);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  group('AssenSidebarShell', () {
    testWidgets('delegates to the bottom tab bar at compact width', (
      tester,
    ) async {
      _setWidth(tester, 390);
      await tester.pumpWidget(_host());

      expect(find.byType(AssenTabBar), findsOneWidget);
      expect(find.byType(NavigationRail), findsNothing);
      expect(find.byKey(const Key('assenDesktopSidebar')), findsNothing);
    });

    testWidgets('delegates to a collapsed rail at medium width', (
      tester,
    ) async {
      _setWidth(tester, 768);
      await tester.pumpWidget(_host());

      final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
      expect(rail.extended, isFalse);
      expect(find.byKey(const Key('assenDesktopSidebar')), findsNothing);
    });

    testWidgets('delegates to an extended rail at expanded width', (
      tester,
    ) async {
      _setWidth(tester, 1000); // expanded class (840-1199): rail, not sidebar
      await tester.pumpWidget(_host());

      final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
      expect(rail.extended, isTrue);
      expect(find.byKey(const Key('assenDesktopSidebar')), findsNothing);
    });

    testWidgets('shows a fixed 256px persistent sidebar at large width', (
      tester,
    ) async {
      _setWidth(tester, 1300); // clearly inside the large class (1200-1599)
      await tester.pumpWidget(_host());

      expect(find.byType(NavigationRail), findsNothing);
      final sidebar = find.byKey(const Key('assenDesktopSidebar'));
      expect(sidebar, findsOneWidget);
      expect(tester.getSize(sidebar).width, AssenLayout.sidebarWidth);
      // Full labels + the badge render in the sidebar.
      for (final item in _items) {
        expect(find.text(item.label), findsOneWidget);
      }
      expect(find.byType(AssenCountBadge), findsOneWidget);
      expect(find.byKey(const Key('shell-body')), findsOneWidget);
    });

    testWidgets('keeps the 256px sidebar at extra-large width', (tester) async {
      _setWidth(tester, 2560);
      await tester.pumpWidget(_host());

      final sidebar = find.byKey(const Key('assenDesktopSidebar'));
      expect(sidebar, findsOneWidget);
      expect(tester.getSize(sidebar).width, AssenLayout.sidebarWidth);
      expect(find.byType(NavigationRail), findsNothing);
    });
  });
}
