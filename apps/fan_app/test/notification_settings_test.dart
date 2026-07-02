import 'package:fan_app/app.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
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

/// Pins compact mobile width while giving the settings list enough height.
void _useCompactTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(390, 1800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets(
    'notification settings is reachable from My and toggles locally',
    (
      tester,
    ) async {
      _useCompactTallSurface(tester);
      await _pumpSignedInApp(tester);

      await tester.tap(find.text('마이').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('알림 설정'));
      await tester.pumpAndSettle();

      expect(find.byType(AssenTabBar), findsOneWidget);
      expect(find.byType(AssenNotificationSettingsTemplate), findsOneWidget);
      expect(find.text('서비스 알림'), findsOneWidget);
      expect(find.text('예약 상태 변경'), findsOneWidget);
      expect(find.text('이벤트 공지'), findsOneWidget);
      expect(find.text('쿠폰 발급·만료'), findsOneWidget);
      expect(find.text('최애 출근 요약'), findsOneWidget);
      expect(find.text('혜택·프로모션 소식'), findsOneWidget);
      expect(find.text('야간 수신 (21시–8시)'), findsOneWidget);

      final initialSwitches = tester.widgetList<Switch>(find.byType(Switch));
      final initialNightSwitch = initialSwitches.elementAt(5);
      expect(initialNightSwitch.value, false);
      expect(initialNightSwitch.onChanged, isNull);

      await tester.tap(find.byType(Switch).at(4));
      await tester.pumpAndSettle();

      final enabledSwitches = tester.widgetList<Switch>(find.byType(Switch));
      final enabledNightSwitch = enabledSwitches.elementAt(5);
      expect(enabledNightSwitch.onChanged, isNotNull);

      await tester.tap(find.byType(Switch).at(4));
      await tester.pumpAndSettle();

      expect(find.textContaining('광고성 알림 수신 거부 처리됨'), findsOneWidget);

      // ASS-113 prohibited notification policy: this screen must not introduce
      // real-time store presence or location-triggered notification categories.
      expect(find.textContaining(RegExp('실시간|지금 매장|위치')), findsNothing);
    },
  );
}
