// Tests for the notification write actions (M5 write wiring): the repository's
// mark-read / mark-all-read transport, the controller's optimistic flips (with
// rollback), and the 알림 screen's per-row tap + "모두 읽음" action. No network.

import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_controller.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:assen_mobile/src/notifications/notifications_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

import 'support/recording_dio.dart';

AppNotification _notif(String id, String title, {bool read = false}) =>
    AppNotification(
      id: id,
      kind: 'comment',
      title: title,
      createdAt: DateTime(2026, 7),
      read: read,
    );

/// A notifications repository returning a fixed feed; its writes fail when
/// [failWrites] is set, so the rollback path is exercisable.
class _WritableNotifRepo implements NotificationsRepository {
  _WritableNotifRepo({required this.items, this.failWrites = false});

  final List<AppNotification> items;
  final bool failWrites;

  @override
  Future<List<AppNotification>> fetchNotifications() async => items;

  @override
  Future<AppNotification> markRead(String id) async {
    if (failWrites) throw Exception('boom');
    return items.firstWhere((n) => n.id == id).copyWith(read: true);
  }

  @override
  Future<int> markAllRead() async {
    if (failWrites) throw Exception('boom');
    return items.where((n) => !n.read).length;
  }
}

Widget _host(NotificationsRepository repo) => ProviderScope(
  overrides: [notificationsRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const NotificationsScreen(),
  ),
);

void main() {
  group('NotificationsRepository write transport', () {
    test('markRead POSTs the read endpoint and parses the row', () async {
      final adapter = RecordingAdapter(
        body: {
          'id': 'n1',
          'kind': 'comment',
          'title': '새 댓글이 달렸어요',
          'href': '',
          'read': true,
          'created_at': '2026-07-06T09:00:00Z',
        },
      );
      final repo = NotificationsRepository(recordingDio(adapter));

      final row = await repo.markRead('n1');

      expect(row.read, isTrue);
      expect(adapter.last.method, 'POST');
      expect(adapter.last.path, '/api/notifications/n1/read');
    });

    test('markAllRead POSTs read-all and parses the updated count', () async {
      final adapter = RecordingAdapter(body: {'updated': 3});
      final repo = NotificationsRepository(recordingDio(adapter));

      final updated = await repo.markAllRead();

      expect(updated, 3);
      expect(adapter.last.method, 'POST');
      expect(adapter.last.path, '/api/notifications/read-all');
    });

    test('markRead translates a 401 into the auth-required marker', () async {
      final adapter = RecordingAdapter(status: 401, body: {'detail': 'nope'});
      final repo = NotificationsRepository(recordingDio(adapter));

      await expectLater(
        repo.markRead('n1'),
        throwsA(isA<NotificationsAuthRequiredException>()),
      );
    });
  });

  group('NotificationsController write flips', () {
    test('markRead flips one row, keeping it on a success', () async {
      final repo = _WritableNotifRepo(
        items: [_notif('n1', 'a'), _notif('n2', 'b', read: true)],
      );
      final container = ProviderContainer(
        overrides: [notificationsRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(notificationsControllerProvider.future);

      await container
          .read(notificationsControllerProvider.notifier)
          .markRead('n1');

      final rows = container.read(notificationsControllerProvider).value!;
      expect(rows.firstWhere((n) => n.id == 'n1').read, isTrue);
    });

    test('markRead rolls the row back when the write fails', () async {
      final repo = _WritableNotifRepo(
        items: [_notif('n1', 'a')],
        failWrites: true,
      );
      final container = ProviderContainer(
        overrides: [notificationsRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(notificationsControllerProvider.future);

      await container
          .read(notificationsControllerProvider.notifier)
          .markRead('n1');

      final rows = container.read(notificationsControllerProvider).value!;
      expect(rows.single.read, isFalse); // rolled back
    });

    test('markAllRead flips every unread row on a success', () async {
      final repo = _WritableNotifRepo(
        items: [_notif('n1', 'a'), _notif('n2', 'b')],
      );
      final container = ProviderContainer(
        overrides: [notificationsRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(notificationsControllerProvider.future);

      await container
          .read(notificationsControllerProvider.notifier)
          .markAllRead();

      final rows = container.read(notificationsControllerProvider).value!;
      expect(rows.every((n) => n.read), isTrue);
    });

    test('markAllRead rolls the list back when the write fails', () async {
      final repo = _WritableNotifRepo(
        items: [_notif('n1', 'a'), _notif('n2', 'b')],
        failWrites: true,
      );
      final container = ProviderContainer(
        overrides: [notificationsRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(notificationsControllerProvider.future);

      await container
          .read(notificationsControllerProvider.notifier)
          .markAllRead();

      final rows = container.read(notificationsControllerProvider).value!;
      expect(rows.every((n) => !n.read), isTrue); // rolled back
    });
  });

  group('NotificationsScreen write controls', () {
    testWidgets('tapping an unread row marks it read', (tester) async {
      final repo = _WritableNotifRepo(items: [_notif('n1', '새 댓글')]);
      await tester.pumpWidget(_host(repo));
      await tester.pump();
      await tester.pump();

      // The unread row offers the "모두 읽음" action; after tapping the row it is
      // read, so the (now-nothing-unread) action disappears.
      expect(find.byTooltip('모두 읽음'), findsOneWidget);
      await tester.tap(find.text('새 댓글'));
      await tester.pump();
      expect(find.byTooltip('모두 읽음'), findsNothing);
    });

    testWidgets('the app-bar action marks every row read', (tester) async {
      final repo = _WritableNotifRepo(
        items: [_notif('n1', '가'), _notif('n2', '나')],
      );
      await tester.pumpWidget(_host(repo));
      await tester.pump();
      await tester.pump();

      await tester.tap(find.byTooltip('모두 읽음'));
      await tester.pump();
      expect(find.byTooltip('모두 읽음'), findsNothing);
    });
  });
}
