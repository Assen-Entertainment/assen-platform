import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenNotificationSettingsTemplate', () {
    testWidgets('renders six rows with default switch states', (tester) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: AssenNotificationSettingsTemplate(
            servicePreferences: _servicePrefs,
            benefitPreferences: _benefitPrefs,
            onPreferenceChanged: (_, {required enabled}) {},
          ),
        ),
      );

      expect(find.text('알림'), findsWidgets);
      expect(find.text('서비스 알림'), findsOneWidget);
      expect(find.text('혜택(광고성) 알림'), findsOneWidget);
      expect(find.text('예약 상태 변경'), findsOneWidget);
      expect(find.text('확정·변경·취소 알림'), findsOneWidget);
      expect(find.text('이벤트 공지'), findsOneWidget);
      expect(find.text('생탄제·테마데이 소식'), findsOneWidget);
      expect(find.text('쿠폰 발급·만료'), findsOneWidget);
      expect(find.text('만료 3일 전에 알려드려요'), findsOneWidget);
      expect(find.text('최애 출근 요약'), findsOneWidget);
      expect(find.text('주 1회, 등록한 캐스트만'), findsOneWidget);
      expect(find.text('혜택·프로모션 소식'), findsOneWidget);
      expect(find.text('동의 시 처리 일시를 안내해 드려요'), findsOneWidget);
      expect(find.text('야간 수신 (21시–8시)'), findsOneWidget);
      expect(find.text('광고성 알림의 야간 발송 동의'), findsOneWidget);

      final switches = tester.widgetList<Switch>(find.byType(Switch)).toList();
      expect(switches, hasLength(6));
      expect(
        switches.take(4).map((switchWidget) => switchWidget.value).toList(),
        [true, true, true, true],
      );
      expect(switches[4].value, false);
      expect(switches[5].value, false);
      expect(switches[5].onChanged, isNull);
    });

    testWidgets('calls onChanged with the preference id', (tester) async {
      String? changedId;
      bool? changedValue;

      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: AssenNotificationSettingsTemplate(
            servicePreferences: _servicePrefs,
            benefitPreferences: _benefitPrefs,
            onPreferenceChanged: (id, {required enabled}) {
              changedId = id;
              changedValue = enabled;
            },
          ),
        ),
      );

      await tester.tap(find.byType(Switch).at(1));
      await tester.pump();

      expect(changedId, 'events');
      expect(changedValue, false);
    });
  });
}

const List<AssenNotificationPref> _servicePrefs = [
  AssenNotificationPref(
    id: 'reservation',
    title: '예약 상태 변경',
    subtitle: '확정·변경·취소 알림',
    enabled: true,
  ),
  AssenNotificationPref(
    id: 'events',
    title: '이벤트 공지',
    subtitle: '생탄제·테마데이 소식',
    enabled: true,
  ),
  AssenNotificationPref(
    id: 'coupons',
    title: '쿠폰 발급·만료',
    subtitle: '만료 3일 전에 알려드려요',
    enabled: true,
  ),
  AssenNotificationPref(
    id: 'favorite_summary',
    title: '최애 출근 요약',
    subtitle: '주 1회, 등록한 캐스트만',
    enabled: true,
  ),
];

const List<AssenNotificationPref> _benefitPrefs = [
  AssenNotificationPref(
    id: 'promotions',
    title: '혜택·프로모션 소식',
    subtitle: '동의 시 처리 일시를 안내해 드려요',
    enabled: false,
  ),
  AssenNotificationPref(
    id: 'night_promotions',
    title: '야간 수신 (21시–8시)',
    subtitle: '광고성 알림의 야간 발송 동의',
    enabled: false,
    disabled: true,
  ),
];

/// Sizes the test view so every settings row builds without scrolling.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}
