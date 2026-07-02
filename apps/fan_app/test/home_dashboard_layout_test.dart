import 'package:fan_app/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [HomeScreen] in a minimal router so its responsive home layout can be
/// pumped at different surface widths (ASS-147 desktop optimization).
Widget _host() {
  final router = GoRouter(
    initialLocation: '/home',
    routes: [
      GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
      GoRoute(
        path: '/qr',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('QR_STUB'))),
      ),
      GoRoute(
        path: '/cast/:id',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('CAST_STUB'))),
      ),
    ],
  );
  return MaterialApp.router(theme: AssenTheme.light(), routerConfig: router);
}

void _setSurface(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets(
    'expanded width lays the stamp and schedule sections side by side',
    (tester) async {
      _setSurface(tester, const Size(1280, 2000));
      await tester.pumpWidget(_host());
      await tester.pumpAndSettle();

      final stamp = tester.getRect(find.text('방문 스탬프'));
      final schedule = tester.getRect(find.text('오늘의 출근'));

      // Two-column dashboard: stamp section is left of the schedule section and
      // the two share a row (their vertical ranges overlap).
      expect(stamp.right, lessThanOrEqualTo(schedule.left));
      expect(stamp.top, lessThan(schedule.bottom));
      expect(schedule.top, lessThan(stamp.bottom));
    },
  );

  testWidgets('compact width stacks the schedule below the stamp section', (
    tester,
  ) async {
    _setSurface(tester, const Size(390, 3000));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    final stamp = tester.getRect(find.text('방문 스탬프'));
    final schedule = tester.getRect(find.text('오늘의 출근'));

    // Single stacked column: the schedule section sits below the stamp section.
    expect(schedule.top, greaterThan(stamp.bottom));
  });
}
