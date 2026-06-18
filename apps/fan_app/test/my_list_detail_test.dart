import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the My hub inline list-detail (ASS-147 Slice 4): at the QHD desktop
/// width the account menu sits beside the selected sub-page body; below the
/// large class the menu is a full-width list and tapping a row pushes the child
/// route (the unchanged mobile flow).
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
  testWidgets('at 2560 the My menu sits left of the selected detail pane', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.pointsHistory);
    await tester.pumpAndSettle();

    expect(find.byType(AssenPointsHistoryBody), findsOneWidget);

    final menu = tester.getRect(find.text('회원증 QR'));
    final detail = tester.getRect(find.byType(AssenPointsHistoryBody));
    // Menu pane is entirely left of the detail pane, and the two overlap
    // vertically (side by side, not stacked).
    expect(menu.right, lessThanOrEqualTo(detail.left));
    expect(menu.top, lessThan(detail.bottom));
    expect(detail.top, lessThan(menu.bottom));
  });

  testWidgets('below large the menu is a full-width list and a tap pushes', (
    tester,
  ) async {
    _setSurface(tester, const Size(390, 2400));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.my);
    await tester.pumpAndSettle();

    // Stacked hub — no inline detail pane.
    expect(find.byType(AssenPointsHistoryBody), findsNothing);

    await tester.tap(find.text('포인트 내역'));
    await tester.pumpAndSettle();

    // Selecting pushed the full-screen child route (no inline detail).
    expect(find.byType(AssenPointsHistoryTemplate), findsOneWidget);
    expect(find.byType(AssenPointsHistoryBody), findsNothing);
  });
}
