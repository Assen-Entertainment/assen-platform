// Contract + render tests for the 알림 tab: AppNotification.fromJson parses the
// server shape, a 401 (NotificationsAuthRequiredException) shows the login
// empty state, and an authenticated feed renders its rows. No network.

import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:assen_mobile/src/notifications/notifications_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in returning a fixed feed or the auth-required error.
class _FakeNotificationsRepository implements NotificationsRepository {
  _FakeNotificationsRepository.items(List<AppNotification> items)
    : _items = items,
      _error = null;
  _FakeNotificationsRepository.authRequired()
    : _items = null,
      _error = const NotificationsAuthRequiredException();

  final List<AppNotification>? _items;
  final Exception? _error;

  @override
  Future<List<AppNotification>> fetchNotifications() async {
    final error = _error;
    if (error != null) throw error;
    return _items!;
  }
}

Widget _host(NotificationsRepository repository) => ProviderScope(
  overrides: [
    notificationsRepositoryProvider.overrideWithValue(repository),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const NotificationsScreen(),
  ),
);

void main() {
  test('AppNotification.fromJson parses the NotificationOut shape', () {
    final notification = AppNotification.fromJson(const {
      'id': 'n1',
      'kind': 'order',
      'title': '주문이 접수되었어요',
      'href': '/orders/1',
      'read': false,
      'created_at': '2026-07-06T09:00:00Z',
    });
    expect(notification.title, '주문이 접수되었어요');
    expect(notification.kind, 'order');
    expect(notification.read, isFalse);
    expect(notification.createdAt.isUtc, isTrue);
  });

  test('AppNotification.fromJson throws on a missing created_at', () {
    expect(
      () => AppNotification.fromJson(const {
        'id': 'n1',
        'kind': 'order',
        'title': '제목',
      }),
      throwsA(isA<ArgumentError>()),
    );
  });

  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeNotificationsRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget); // the CTA
  });

  testWidgets('an authenticated feed renders its rows', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeNotificationsRepository.items([
          AppNotification(
            id: 'n1',
            kind: 'comment',
            title: '새 댓글이 달렸어요',
            createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
          ),
        ]),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('새 댓글이 달렸어요'), findsOneWidget);
    expect(find.text('5분 전'), findsOneWidget);
  });

  testWidgets('an empty feed shows the empty state', (tester) async {
    await tester.pumpWidget(
      _host(_FakeNotificationsRepository.items(const [])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('알림이 없어요'), findsOneWidget);
  });
}
