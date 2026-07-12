import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 알림 tab's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a [NotificationsAuthRequiredException] in the error state, which the
/// screen maps to the "로그인이 필요해요" branch rather than a failure.
class NotificationsController extends AsyncNotifier<List<AppNotification>>
    with RefreshableAsyncNotifier<List<AppNotification>> {
  @override
  Future<List<AppNotification>> build() {
    return ref.watch(notificationsRepositoryProvider).fetchNotifications();
  }

  @override
  Future<List<AppNotification>> fetch() =>
      ref.read(notificationsRepositoryProvider).fetchNotifications();

  /// Marks the notification [id] read, optimistically.
  ///
  /// Flips that row's [AppNotification.read] to true immediately (the unread
  /// dot clears), then confirms with the server — rolling the list back to
  /// its pre-toggle value if the write fails. A no-op when the row is already
  /// read, unknown, or the feed is not in its data state.
  Future<void> markRead(String id) async {
    final current = state.value;
    if (current == null) return;
    final index = current.indexWhere((n) => n.id == id);
    if (index < 0 || current[index].read) return;
    final optimistic = [...current];
    optimistic[index] = current[index].copyWith(read: true);
    state = AsyncData(optimistic);
    try {
      await ref.read(notificationsRepositoryProvider).markRead(id);
    } on Object {
      // The write failed: restore the pre-toggle list so the dot doesn't lie.
      state = AsyncData(current);
    }
  }

  /// Marks every unread notification read, optimistically.
  ///
  /// Flips all rows to read at once (clearing every unread dot), then confirms
  /// with the server — rolling the whole list back if the write fails. A no-op
  /// when nothing is unread or the feed is not in its data state.
  Future<void> markAllRead() async {
    final current = state.value;
    if (current == null || current.every((n) => n.read)) return;
    state = AsyncData([
      for (final n in current) n.read ? n : n.copyWith(read: true),
    ]);
    try {
      await ref.read(notificationsRepositoryProvider).markAllRead();
    } on Object {
      // The write failed: restore the pre-toggle list.
      state = AsyncData(current);
    }
  }
}

/// Exposes the notification feed and its [NotificationsController].
final notificationsControllerProvider =
    AsyncNotifierProvider<NotificationsController, List<AppNotification>>(
      NotificationsController.new,
      retry: noRetry,
    );
