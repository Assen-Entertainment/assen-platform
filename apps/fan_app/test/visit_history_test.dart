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

/// Gives the visit timeline enough room to build grouped lazy content.
void _useTallSurface(WidgetTester tester) {
  // ASS-141: 폭은 compact(390), 높이는 긴 목록 잘림 방지용으로 유지.
  tester.view.physicalSize = const Size(390, 3000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('visit history is reachable from My and hides voided visits', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    await tester.tap(find.text('마이').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('나의 하츠코이 기록'));
    await tester.pumpAndSettle();

    expect(find.byType(AssenTabBar), findsOneWidget);
    expect(find.text('나의 하츠코이 기록'), findsOneWidget);
    expect(find.text('12회'), findsOneWidget);
    expect(find.text('12번의 귀가'), findsOneWidget);
    expect(find.text('6월'), findsOneWidget);
    expect(find.text('5월'), findsOneWidget);
    expect(find.text('첫 방문'), findsOneWidget);
    expect(find.text('+50 P'), findsWidgets);
    expect(find.text('−1장'), findsWidgets);
    expect(find.text('무효 처리된 방문 · 테스트'), findsNothing);
  });
}
