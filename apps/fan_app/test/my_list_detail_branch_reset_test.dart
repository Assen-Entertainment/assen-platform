import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the My hub detail reset (ASS-147 Slice 4, M3/R8): the selection is
/// URL-derived (each `/my/*` screen owns its sub-page), so leaving to another
/// branch and returning to the `/my` root clears the detail pane — no app-global
/// provider holds a stale sub-page.
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
  testWidgets('returning to the /my root resets the detail selection', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);

    // Select the points sub-page — the detail pane shows the points body.
    _router(tester).go(FanRoutes.pointsHistory);
    await tester.pumpAndSettle();
    expect(find.byType(AssenPointsHistoryBody), findsOneWidget);

    // Leave to another branch (home).
    _router(tester).go(FanRoutes.home);
    await tester.pumpAndSettle();
    expect(find.byType(AssenPointsHistoryBody), findsNothing);

    // Return to the My hub root: the detail pane is reset to the prompt.
    _router(tester).go(FanRoutes.my);
    await tester.pumpAndSettle();

    expect(find.byType(AssenPointsHistoryBody), findsNothing);
    expect(find.text('메뉴를 선택해 주세요'), findsOneWidget);
  });
}
