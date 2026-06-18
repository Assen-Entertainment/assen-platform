import 'package:fan_app/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [HomeScreen] INSIDE [AssenSidebarShell] so the desktop body width is
/// the window minus the 256px sidebar — the realistic geometry. (The existing
/// `home_dashboard_layout_test` pumps HomeScreen standalone at 1280 to pin the
/// stamp/schedule pair; this test pins the in-shell wide behaviour at 2560.)
Widget _host() {
  Widget stub(String label) => Scaffold(body: Center(child: Text(label)));
  final router = GoRouter(
    initialLocation: '/home',
    routes: [
      GoRoute(
        path: '/home',
        builder: (context, state) => AssenSidebarShell(
          currentIndex: 0,
          onChanged: _noop,
          items: _items,
          body: const HomeScreen(),
        ),
      ),
      GoRoute(path: '/my', builder: (c, s) => stub('MY')),
      GoRoute(path: '/schedule', builder: (c, s) => stub('SCHEDULE')),
      GoRoute(path: '/qr', builder: (c, s) => stub('QR')),
      GoRoute(path: '/events', builder: (c, s) => stub('EVENTS')),
      GoRoute(path: '/cast/:id', builder: (c, s) => stub('CAST')),
    ],
  );
  return MaterialApp.router(theme: AssenTheme.light(), routerConfig: router);
}

const _items = [
  AssenTabItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: '홈'),
  AssenTabItem(icon: Icons.person_outline, label: '마이'),
];

void _noop(int _) {}

void _setSurface(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

bool _overlapsVertically(Rect a, Rect b) =>
    a.top < b.bottom && b.top < a.bottom;

void main() {
  testWidgets(
    'at 2560 the home is a multi-column feed beside a membership rail',
    (tester) async {
      _setSurface(tester, const Size(2560, 1440));
      await tester.pumpWidget(_host());
      await tester.pumpAndSettle();

      final stamp = tester.getRect(find.text('방문 스탬프'));
      final schedule = tester.getRect(find.text('오늘의 출근'));
      final favorites = tester.getRect(find.text('최애 캐스트'));
      final membership = tester.getRect(find.text('체리체리'));

      // Feed has >=3 columns: stamp, schedule and favorites share the first
      // row, left-to-right.
      expect(stamp.left, lessThan(schedule.left));
      expect(schedule.left, lessThan(favorites.left));
      expect(_overlapsVertically(stamp, schedule), isTrue);
      expect(_overlapsVertically(schedule, favorites), isTrue);

      // The membership rail sits to the RIGHT of the feed (supporting pane).
      expect(membership.left, greaterThanOrEqualTo(favorites.right));
    },
  );

  testWidgets('at 390 the home stacks in a single column', (tester) async {
    _setSurface(tester, const Size(390, 3000));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    final stamp = tester.getRect(find.text('방문 스탬프'));
    final schedule = tester.getRect(find.text('오늘의 출근'));
    expect(schedule.top, greaterThan(stamp.bottom));
  });
}
