import 'package:fan_app/screens/schedule_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [ScheduleScreen] in a router so cast-card taps can exercise the
/// `/cast/:id` deep link instead of stopping at widget composition.
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
        builder: (context, state) => Scaffold(
          body: Center(child: Text('CAST_${state.pathParameters['id']}')),
        ),
      ),
    ],
  );
  return MaterialApp.router(theme: AssenTheme.light(), routerConfig: router);
}

/// Gives the schedule sliver list enough viewport height for its lazy children
/// to build deterministically in widget tests.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('favorite chips filter scheduled casts and keep profile links', (
    tester,
  ) async {
    _useTallSurface(tester);
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    expect(find.byType(AssenCastProfileCard), findsNWidgets(3));

    await tester.tap(find.widgetWithText(AssenFilterChip, '유키'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenCastProfileCard), findsOneWidget);

    await tester.tap(find.byType(AssenCastProfileCard));
    await tester.pumpAndSettle();

    expect(find.text('CAST_yuki'), findsOneWidget);
  });

  testWidgets(
    'favorite chip shows a specific empty state when that cast is off',
    (tester) async {
      _useTallSurface(tester);
      await tester.pumpWidget(_host());
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(AssenFilterChip, '베리'));
      await tester.pumpAndSettle();

      expect(find.byType(AssenCastProfileCard), findsNothing);
      expect(find.text('베리 출근 예정이 없어요'), findsOneWidget);
    },
  );
}
