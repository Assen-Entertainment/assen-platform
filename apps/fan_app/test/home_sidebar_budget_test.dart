import 'package:fan_app/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Proves the home feed's column count derives from the LOCAL body width (the
/// window minus the 256px sidebar), not the raw window width (M2).
///
/// Window 1700 is the extra-large class, but after the 256px sidebar the home
/// body is ~1444 (large class) and the feed pane (~980 after the membership
/// rail) yields a 2-column feed. A window-width count would over-count (1700
/// would give 3+ columns). So we assert the feed is 2-up: stamp + schedule
/// share the first row, and favorites wraps to the second — which only happens
/// at two columns, never three.
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

void main() {
  testWidgets(
    'feed column count derives from the sidebar-subtracted body width (1700 '
    'window -> 1444 body -> 2 columns, not 3)',
    (tester) async {
      tester.view.physicalSize = const Size(1700, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_host());
      await tester.pumpAndSettle();

      final stamp = tester.getRect(find.text('방문 스탬프'));
      final schedule = tester.getRect(find.text('오늘의 출근'));
      final favorites = tester.getRect(find.text('최애 캐스트'));

      // Two columns: stamp + schedule on the first row...
      expect(stamp.left, lessThan(schedule.left));
      expect(
        stamp.top < schedule.bottom && schedule.top < stamp.bottom,
        isTrue,
      );
      // ...and favorites wraps to the SECOND row (below stamp). At three
      // columns (a window-width count) it would sit beside schedule on row one.
      expect(favorites.top, greaterThan(stamp.bottom));
    },
  );
}
