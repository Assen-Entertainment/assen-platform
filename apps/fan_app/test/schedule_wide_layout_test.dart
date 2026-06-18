import 'package:fan_app/screens/schedule_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [ScheduleScreen] so its wide (expanded+) cast feed can be pumped at
/// different widths (ASS-147 Slice 2). The existing schedule_filter_test pins
/// filter/empty-state behaviour at 1080; this pins the responsive feed geometry.
Widget _host() {
  final router = GoRouter(
    initialLocation: '/schedule',
    routes: [
      GoRoute(
        path: '/schedule',
        builder: (context, state) => const ScheduleScreen(),
      ),
      GoRoute(
        path: '/cast/:id',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('CAST'))),
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
  testWidgets('at 2560 the working casts lay out in a multi-column feed', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1440));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    // The default day (수 11) has three working casts.
    final cards = find.byType(AssenCastProfileCard);
    expect(cards, findsNWidgets(3));

    final r0 = tester.getRect(cards.at(0));
    final r1 = tester.getRect(cards.at(1));
    final r2 = tester.getRect(cards.at(2));

    // Row-major feed: the three cards share the first row, left-to-right.
    expect(r0.left, lessThan(r1.left));
    expect(r1.left, lessThan(r2.left));
    expect(r0.top < r1.bottom && r1.top < r0.bottom, isTrue);
    expect(r1.top < r2.bottom && r2.top < r1.bottom, isTrue);
  });

  testWidgets('at 390 the working casts stack in a single column', (
    tester,
  ) async {
    _setSurface(tester, const Size(390, 2400));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    final cards = find.byType(AssenCastProfileCard);
    expect(cards, findsNWidgets(3));

    final r0 = tester.getRect(cards.at(0));
    final r1 = tester.getRect(cards.at(1));
    expect(r1.top, greaterThanOrEqualTo(r0.bottom));
  });
}
