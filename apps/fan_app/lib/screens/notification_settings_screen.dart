import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The fan-facing local notification settings screen (F4).
///
/// ASS-143 intentionally keeps all switches in widget-local mock state: no
/// persistence, FCM topic wiring, or delivery preference API is introduced
/// here.
/// The ASS-113 notification body replaces this when backend consent records and
/// actual push delivery are ready.
class NotificationSettingsScreen extends StatefulWidget {
  /// Creates the notification settings screen.
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends State<NotificationSettingsScreen> {
  static const String _reservationId = 'reservation';
  static const String _eventsId = 'events';
  static const String _couponsId = 'coupons';
  static const String _favoriteSummaryId = 'favorite_summary';
  static const String _promotionsId = 'promotions';
  static const String _nightPromotionsId = 'night_promotions';

  final Map<String, bool> _prefs = <String, bool>{
    _reservationId: true,
    _eventsId: true,
    _couponsId: true,
    _favoriteSummaryId: true,
    _promotionsId: false,
    _nightPromotionsId: false,
  };

  @override
  Widget build(BuildContext context) {
    return AssenNotificationSettingsTemplate(
      servicePreferences: [
        AssenNotificationPref(
          id: _reservationId,
          title: '예약 상태 변경',
          subtitle: '확정·변경·취소 알림',
          enabled: _prefs[_reservationId] ?? true,
        ),
        AssenNotificationPref(
          id: _eventsId,
          title: '이벤트 공지',
          subtitle: '생탄제·테마데이 소식',
          enabled: _prefs[_eventsId] ?? true,
        ),
        AssenNotificationPref(
          id: _couponsId,
          title: '쿠폰 발급·만료',
          subtitle: '만료 3일 전에 알려드려요',
          enabled: _prefs[_couponsId] ?? true,
        ),
        AssenNotificationPref(
          id: _favoriteSummaryId,
          title: '최애 출근 요약',
          subtitle: '주 1회, 등록한 캐스트만',
          enabled: _prefs[_favoriteSummaryId] ?? true,
        ),
      ],
      benefitPreferences: [
        AssenNotificationPref(
          id: _promotionsId,
          title: '혜택·프로모션 소식',
          subtitle: '동의 시 처리 일시를 안내해 드려요',
          enabled: _prefs[_promotionsId] ?? false,
        ),
        AssenNotificationPref(
          id: _nightPromotionsId,
          title: '야간 수신 (21시–8시)',
          subtitle: '광고성 알림의 야간 발송 동의',
          enabled: _prefs[_nightPromotionsId] ?? false,
          disabled: !(_prefs[_promotionsId] ?? false),
        ),
      ],
      onPreferenceChanged: _handlePreferenceChanged,
      onBack: () => context.go(FanRoutes.my),
    );
  }

  void _handlePreferenceChanged(String id, {required bool enabled}) {
    setState(() {
      _prefs[id] = enabled;
      if (id == _promotionsId && !enabled) {
        _prefs[_nightPromotionsId] = false;
      }
    });

    if (id == _promotionsId) {
      // The real consent timestamp is recorded by the backend after ASS-90/91.
      final consent = enabled ? '동의' : '거부';
      AssenToast.show(
        context,
        AssenToast(
          message: '${_formatDate(DateTime.now())} 광고성 알림 수신 $consent 처리됨',
        ),
      );
    }
  }
}

String _formatDate(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}.$month.$day';
}
