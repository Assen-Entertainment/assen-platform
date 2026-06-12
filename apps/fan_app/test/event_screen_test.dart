import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

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

void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 3000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void _expectNoPriceText() {
  expect(find.textContaining(RegExp('[0-9,]+원')), findsNothing);
}

void main() {
  testWidgets('event list renders banner, filter tabs, and all card states', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventListTemplate), findsOneWidget);
    expect(find.text('하츠코이'), findsOneWidget);
    expect(find.text('전체'), findsOneWidget);
    expect(find.text('캐스트'), findsOneWidget);
    expect(find.text('이벤트'), findsWidgets);
    expect(find.text('공지'), findsOneWidget);
    expect(find.text('6월 생탄제 — 미오 생일 위크'), findsOneWidget);
    expect(find.text('6.14–6.20 · 한정 메뉴와 특별 체키'), findsOneWidget);
    expect(find.text('미오 생탄제'), findsOneWidget);
    expect(find.text('D-3'), findsOneWidget);
    expect(find.text('예약 가능'), findsOneWidget);
    expect(find.text('딸기 시즌 — 신메뉴 위크'), findsOneWidget);
    expect(find.text('진행중'), findsOneWidget);
    expect(find.text('오늘 참여'), findsOneWidget);
    expect(find.text('5월 어버이날 티 파티'), findsOneWidget);
    expect(find.text('종료'), findsOneWidget);
    expect(find.text('종료됨'), findsOneWidget);
    _expectNoPriceText();

    await tester.tap(find.text('캐스트'));
    await tester.pumpAndSettle();

    expect(find.text('미오 생탄제'), findsOneWidget);
    expect(find.text('딸기 시즌 — 신메뉴 위크'), findsNothing);
    expect(find.text('5월 어버이날 티 파티'), findsNothing);
    _expectNoPriceText();
  });

  testWidgets('tapping upcoming event opens detail', (tester) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.events);
    await tester.pumpAndSettle();

    await tester.tap(find.text('미오 생탄제'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailTemplate), findsOneWidget);
    expect(find.text('6월 14일 (토) 13:00–21:00'), findsOneWidget);
    _expectNoPriceText();
  });

  testWidgets('event detail renders key rows, notice, and reservation CTA', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.eventPath('mio-birthday-week'));
    await tester.pumpAndSettle();

    expect(find.text('미오 생탄제'), findsOneWidget);
    expect(find.text('D-3'), findsOneWidget);
    expect(find.text('미오'), findsWidgets);
    expect(find.text('일정'), findsOneWidget);
    expect(find.text('6월 14일 (토) 13:00–21:00'), findsOneWidget);
    expect(find.text('참여 방법'), findsOneWidget);
    expect(find.text('예약 후 매장 방문'), findsOneWidget);
    expect(find.text('특전'), findsOneWidget);
    expect(find.text('생탄제 한정 체키 + 포토카드'), findsOneWidget);
    expect(find.text('당일 예약 변경은 매장으로 문의해 주세요'), findsOneWidget);
    expect(find.text('이 날짜로 예약하기'), findsOneWidget);
    _expectNoPriceText();

    await tester.tap(find.text('이 날짜로 예약하기'));
    await tester.pumpAndSettle();

    expect(find.text('아직 예약이 없어요'), findsOneWidget);
    _expectNoPriceText();
  });

  testWidgets('ended event detail has no active reservation CTA', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.eventPath('parents-day-tea-party'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailTemplate), findsOneWidget);
    expect(find.text('5월 어버이날 티 파티'), findsOneWidget);
    expect(find.text('종료'), findsOneWidget);
    expect(find.text('이 날짜로 예약하기'), findsNothing);
    _expectNoPriceText();
  });

  testWidgets('unknown event detail renders not-found fallback', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    _router(tester).go(FanRoutes.eventPath('unknown-event'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenEventDetailTemplate), findsNothing);
    expect(find.byType(AssenEmptyState), findsOneWidget);
    expect(find.text('이벤트'), findsOneWidget);
    expect(find.text('이벤트를 찾을 수 없어요'), findsOneWidget);
    expect(find.text('이벤트 목록 보기'), findsOneWidget);
    _expectNoPriceText();
  });
}
