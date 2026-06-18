import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the dense points list at desktop width (ASS-147 Slice 4, O4 — no data
/// table): at the QHD width the points body fills the detail pane rather than a
/// narrow centered reading column. Concrete geometry, not "empty middle" prose.
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
  testWidgets('at 2560 the points body fills the detail pane width', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.pointsHistory);
    await tester.pumpAndSettle();

    final body = tester.getRect(find.byType(AssenPointsHistoryBody));
    // The detail pane spans most of the (sidebar-reduced) My screen width — far
    // wider than a centered reading column. The My screen gets ~2304 (2560
    // minus the 256 sidebar); the detail pane is the surface minus the 300 menu
    // and gaps, so it comfortably exceeds 1200.
    expect(body.width, greaterThan(1200));
  });
}
