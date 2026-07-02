import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: child,
);

const _items = [
  AssenTabItem(
    icon: Icons.home_outlined,
    activeIcon: Icons.home,
    label: 'Home',
  ),
  AssenTabItem(icon: Icons.calendar_month_outlined, label: 'Schedule'),
  AssenTabItem(icon: Icons.event_outlined, label: 'Reserve'),
  AssenTabItem(
    icon: Icons.photo_library_outlined,
    label: 'Cheki',
    badgeCount: 3,
  ),
  AssenTabItem(icon: Icons.person_outline, label: 'My'),
];

void _setLogicalSize(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 900);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Widget _shell({int currentIndex = 0}) {
  return AssenAdaptiveShell(
    currentIndex: currentIndex,
    onChanged: (_) {},
    items: _items,
    body: const SizedBox.expand(
      key: Key('body'),
      child: ColoredBox(color: Colors.transparent),
    ),
  );
}

void main() {
  group('AssenAdaptiveShell', () {
    testWidgets('uses the bottom tab bar at compact width', (tester) async {
      _setLogicalSize(tester, 390);

      await tester.pumpWidget(_host(_shell()));

      expect(find.byType(AssenTabBar), findsOneWidget);
      expect(find.byType(NavigationRail), findsNothing);
    });

    testWidgets('uses a collapsed navigation rail at medium width', (
      tester,
    ) async {
      _setLogicalSize(tester, 768);

      await tester.pumpWidget(_host(_shell()));

      expect(find.byType(NavigationRail), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
      final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
      expect(rail.extended, isFalse);
    });

    testWidgets('uses an extended rail and content column at expanded width', (
      tester,
    ) async {
      _setLogicalSize(tester, 1280);

      await tester.pumpWidget(_host(_shell(currentIndex: 1)));

      final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
      expect(rail.extended, isTrue);
      expect(find.text('Schedule'), findsOneWidget);
      expect(find.byType(AssenContentColumn), findsOneWidget);

      final constrained = tester.widget<ConstrainedBox>(
        find.descendant(
          of: find.byType(AssenContentColumn),
          matching: find.byType(ConstrainedBox),
        ),
      );
      expect(constrained.constraints.maxWidth, AssenLayout.contentMaxWidth);
    });
  });

  group('AssenContentColumn', () {
    testWidgets('limits a wide child to the authored content width', (
      tester,
    ) async {
      _setLogicalSize(tester, 1400);

      await tester.pumpWidget(
        _host(
          const Scaffold(
            body: SizedBox(
              width: 1400,
              child: AssenContentColumn(
                child: SizedBox.expand(key: Key('content-child')),
              ),
            ),
          ),
        ),
      );

      expect(
        tester.getSize(find.byKey(const Key('content-child'))).width,
        AssenLayout.contentMaxWidth,
      );
    });
  });
}
