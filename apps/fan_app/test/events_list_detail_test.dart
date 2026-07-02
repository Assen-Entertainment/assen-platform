import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the wide (large+) events list-detail (ASS-147 Slice 3): at the QHD
/// desktop width the event feed sits beside a detail pane that mounts the
/// selected event's body, while below the large class selecting an event still
/// pushes `/events/:id` (the unchanged mobile flow).
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
  testWidgets('at 2560 the event feed sits left of the selected detail pane', (
    tester,
  ) async {
    _setSurface(tester, const Size(2560, 1600));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    // No selection yet: the detail pane prompts the user to pick an event.
    expect(find.text('이벤트를 선택해 주세요'), findsOneWidget);
    expect(find.byType(AssenEventDetailBody), findsNothing);

    await tester.tap(find.text('미오 생탄제'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailBody), findsOneWidget);

    final feed = tester.getRect(find.byType(AssenFeedGrid));
    final detail = tester.getRect(find.byType(AssenEventDetailBody));
    // List pane (feed) is entirely left of the detail pane, and the two overlap
    // vertically (side by side, not stacked).
    expect(feed.right, lessThanOrEqualTo(detail.left));
    expect(feed.top, lessThan(detail.bottom));
    expect(detail.top, lessThan(feed.bottom));

    // The detail pane holds the selected event's body content.
    expect(
      find.descendant(
        of: find.byType(AssenEventDetailBody),
        matching: find.text('6월 14일 (일) 13:00–21:00'),
      ),
      findsOneWidget,
    );
  });

  testWidgets('below expanded, selecting an event pushes the detail route', (
    tester,
  ) async {
    _setSurface(tester, const Size(700, 3000));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    // Mobile/tablet stacked list — no inline detail pane.
    expect(find.byType(AssenEventListTemplate), findsOneWidget);
    expect(find.byType(AssenEventDetailBody), findsNothing);

    await tester.tap(find.text('미오 생탄제'));
    await tester.pumpAndSettle();

    // Selecting pushed the full detail route (no inline list-detail).
    expect(find.byType(AssenEventDetailTemplate), findsOneWidget);
    expect(find.byType(AssenEventDetailBody), findsNothing);
  });

  testWidgets('no dead zone just above 1200dp: a card tap still navigates', (
    tester,
  ) async {
    // 1220 is in the band [1200, 1240) where gating on the RAW width would
    // enter the wide path but the screen-margin-padded list-detail scaffold
    // would collapse to list-only — a tap with nowhere to go. The screen gates
    // on the padded content width, so 1220 (content 1180 < 1200) stays on the
    // mobile push path and a tap reaches the detail route.
    _setSurface(tester, const Size(1220, 2000));
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventListTemplate), findsOneWidget);

    await tester.tap(find.text('미오 생탄제'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailTemplate), findsOneWidget);
  });
}
