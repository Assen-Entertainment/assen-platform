import 'dart:ui' show Size;

import 'package:fan_app/app.dart';
import 'package:features/features.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps the full fan app with an authenticated mock session.
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

/// Pins compact mobile width while giving the read-only ledger enough height.
void _useCompactTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(390, 2600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('points history is reachable from My and stays point-only', (
    tester,
  ) async {
    _useCompactTallSurface(tester);
    await _pumpSignedInApp(tester);

    await tester.tap(find.text('마이').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('포인트 내역'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenTabBar), findsOneWidget);
    expect(find.text('포인트 내역'), findsOneWidget);
    expect(find.text('보유 포인트'), findsOneWidget);
    expect(find.text('1,250 P'), findsOneWidget);
    expect(find.text('6월'), findsOneWidget);
    expect(find.text('5월'), findsOneWidget);
    expect(find.text('12번째 방문 적립'), findsOneWidget);
    expect(find.text('생탄제 이벤트 보너스'), findsOneWidget);
    expect(find.text('포인트로 결제'), findsOneWidget);
    expect(find.text('+50 P'), findsWidgets);
    expect(find.text('−500 P'), findsOneWidget);

    // ASS-139/ASS-142 approval gate: point history must not imply coupon value,
    // discounts, or cash-equivalent pricing in read-only mock UI.
    expect(find.textContaining(RegExp('할인|원|쿠폰')), findsNothing);
  });
}
