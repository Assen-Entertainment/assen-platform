import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the list-detail selection reset (ASS-147 Slice 3, M3/R8): the wide
/// events detail pane must not carry a stale selection across navigation. The
/// selection lives in screen-local state on the out-of-shell `/events` route, so
/// leaving to another surface and returning disposes/recreates the screen and
/// the detail pane resets — never an app-global provider that would persist.
Future<void> _pumpSignedInApp(WidgetTester tester) async {
  final repo = MockAuthRepository();
  addTearDown(repo.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const FanApp(),
    ),
  );
  await tester.pumpAndSettle();

  await repo.signIn(identifier: 'fan@x', password: 'pw');
  await tester.pumpAndSettle();
}

GoRouter _router(WidgetTester tester) =>
    GoRouter.of(tester.element(find.byType(Navigator).first));

void _setSurface(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('returning to the events surface resets the detail selection', (
    tester,
  ) async {
    _setSurface(tester, const Size(1400, 2000));
    await _pumpSignedInApp(tester);

    // Select an event in the wide list-detail.
    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();
    await tester.tap(find.text('미오 생탄제'));
    await tester.pumpAndSettle();
    expect(find.byType(AssenEventDetailBody), findsOneWidget);

    // Leave to another surface (the home branch).
    _router(tester).go(FanRoutes.home);
    await tester.pumpAndSettle();
    expect(find.byType(AssenEventDetailBody), findsNothing);

    // Return to events: the detail pane is reset (no stale selection).
    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailBody), findsNothing);
    expect(find.text('이벤트를 선택해 주세요'), findsOneWidget);
    expect(find.text('6월 14일 (일) 13:00–21:00'), findsNothing);
  });
}
