import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 알림 tab's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a [NotificationsAuthRequiredException] in the error state, which the
/// screen maps to the "로그인이 필요해요" branch rather than a failure.
class NotificationsController extends AsyncNotifier<List<AppNotification>> {
  @override
  Future<List<AppNotification>> build() {
    return ref.watch(notificationsRepositoryProvider).fetchNotifications();
  }

  /// Re-fetches the feed, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(notificationsRepositoryProvider).fetchNotifications(),
    );
  }
}

/// Exposes the notification feed and its [NotificationsController].
final notificationsControllerProvider =
    AsyncNotifierProvider<NotificationsController, List<AppNotification>>(
      NotificationsController.new,
      retry: noRetry,
    );
