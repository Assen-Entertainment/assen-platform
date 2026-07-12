import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/notifications` returns 401 (the caller is signed out).
///
/// A typed marker (not a generic error) so the 알림 screen can branch to the
/// "로그인이 필요해요" state rather than the generic retry error. This is the common
/// path today: the app ships signed-out, so the fan notifications endpoint
/// answers 401 until real login lands (E6 gate).
class NotificationsAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const NotificationsAuthRequiredException();

  @override
  String toString() => 'NotificationsAuthRequiredException';
}

/// Fetches the signed-in fan's notification feed from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class NotificationsRepository {
  /// Creates a repository backed by [_dio].
  const NotificationsRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's notifications via `GET /api/notifications`.
  ///
  /// Maps the `NotificationPage` envelope (`{items, next_cursor}`) into a list
  /// of [AppNotification]s; only the first page is read here (cursor paging is
  /// a follow-up). A 401 is translated into a
  /// [NotificationsAuthRequiredException] so the screen shows the
  /// login-required state; other transport errors propagate to the error state.
  ///
  /// The envelope is parsed strictly: the `items` array must be present (an
  /// empty array is the empty feed), but a *missing* key is a contract
  /// violation and throws (an [ArgumentError] via [requireList]) rather than
  /// silently showing an empty feed. The discovery repository stays lenient
  /// (R7); only the newer search/notifications envelopes are strict.
  Future<List<AppNotification>> fetchNotifications() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/notifications',
      );
      final body = response.data ?? const <String, dynamic>{};
      final items = requireList(body, 'items');
      return items
          .map((item) => AppNotification.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const NotificationsAuthRequiredException();
      }
      rethrow;
    }
  }

  /// Marks one notification read via `POST /api/notifications/{id}/read`.
  ///
  /// Returns the server's updated `NotificationOut` (with `read: true`) so the
  /// controller can reconcile its optimistic flip. A 401 becomes a
  /// [NotificationsAuthRequiredException]; other transport errors (e.g. a 404
  /// when the row is not the caller's) propagate so the controller can roll the
  /// row back.
  Future<AppNotification> markRead(String id) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/notifications/${Uri.encodeComponent(id)}/read',
      );
      return AppNotification.fromJson(
        response.data ?? const <String, dynamic>{},
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const NotificationsAuthRequiredException();
      }
      rethrow;
    }
  }

  /// Marks every unread notification read via
  /// `POST /api/notifications/read-all`.
  ///
  /// Returns the number of rows the server changed (`{updated}`). A 401 becomes
  /// a [NotificationsAuthRequiredException]; other transport errors propagate
  /// so the controller can roll its optimistic all-read flip back.
  Future<int> markAllRead() async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/notifications/read-all',
      );
      final body = response.data ?? const <String, dynamic>{};
      return requireInt(body, 'updated');
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const NotificationsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [NotificationsRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the screen can render mock feeds
/// (or the 401 branch) without a network.
final notificationsRepositoryProvider = Provider<NotificationsRepository>(
  (ref) => NotificationsRepository(ref.watch(dioProvider)),
);
