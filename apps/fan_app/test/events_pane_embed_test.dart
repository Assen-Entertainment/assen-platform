import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the pane-embed contract (ASS-147 Slice 3, Rec 1): the event body
/// mounted in the wide list-detail pane renders NO nested AppBar and NO bottom
/// CTA, and its affordances act on the pane (close clears the selection
/// without popping the route) rather than on global navigation.
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

Future<void> _openSelectedEvent(WidgetTester tester) async {
  _router(tester).go(FanRoutes.events);
  await tester.pumpAndSettle();
  await tester.tap(find.text('미오 생탄제'));
  await tester.pumpAndSettle();
  expect(find.byType(AssenEventDetailBody), findsOneWidget);
}

void main() {
  testWidgets('the embedded detail pane has no nested AppBar or bottom CTA', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);
    await _openSelectedEvent(tester);

    expect(
      find.descendant(
        of: find.byType(AssenEventDetailBody),
        matching: find.byType(AppBar),
      ),
      findsNothing,
    );
    expect(
      find.descendant(
        of: find.byType(AssenEventDetailBody),
        matching: find.byType(AssenBottomCta),
      ),
      findsNothing,
    );
  });

  testWidgets('in-pane close clears the selection without popping the route', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);
    await _openSelectedEvent(tester);

    await tester.tap(
      find.descendant(
        of: find.byType(AssenEventDetailBody),
        matching: find.byIcon(Icons.close),
      ),
    );
    await tester.pumpAndSettle();

    // Selection cleared back to the prompt; the body is gone.
    expect(find.byType(AssenEventDetailBody), findsNothing);
    expect(find.text('이벤트를 선택해 주세요'), findsOneWidget);
    // The surrounding route did NOT pop — still on the events surface.
    expect(find.text('하츠코이'), findsOneWidget);
    expect(
      _router(tester).routerDelegate.currentConfiguration.uri.path,
      FanRoutes.events,
    );
  });

  testWidgets('in-pane reserve runs the pane-supplied reservation action', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);
    await _openSelectedEvent(tester);

    // The reserve affordance is an inline button (not a bottom CTA); tapping it
    // runs the host's reserve action — navigating to the reservation surface.
    await tester.tap(find.text('이 날짜로 예약하기'));
    await tester.pumpAndSettle();

    expect(find.text('아직 예약이 없어요'), findsOneWidget);
  });
}
