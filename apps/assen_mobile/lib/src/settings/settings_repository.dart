import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when a `/api/fan/me` call returns 401 (the caller is signed out).
///
/// A typed marker so the 설정 screen can branch to the "로그인이 필요해요" state rather
/// than the generic retry error. The app ships signed-out, so the fan endpoint
/// (which requires `fan_auth`) answers 401 until real login lands (E6 gate).
class SettingsAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const SettingsAuthRequiredException();

  @override
  String toString() => 'SettingsAuthRequiredException';
}

/// Reads and updates the signed-in fan's own profile for the 설정 screen.
///
/// A thin repository over [Dio] owning the `/api/fan/me` endpoint (read via GET,
/// nickname edit via PATCH) and the JSON→model mapping so the controller/UI stay
/// transport-agnostic. It reuses the shared [FanMe] view model. When the
/// generated `api_client` (P6) lands, this delegates to it instead of Dio.
class SettingsRepository {
  /// Creates a repository backed by [_dio].
  const SettingsRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's profile via `GET /api/fan/me` (auth required).
  ///
  /// A 401 is translated into a [SettingsAuthRequiredException] so the screen
  /// shows the login-required state; other transport errors propagate to the
  /// generic error state. The body is parsed strictly by [FanMe.fromJson].
  Future<FanMe> fetchMe() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/fan/me');
      return FanMe.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }

  /// Updates the fan's own nickname via `PATCH /api/fan/me`.
  ///
  /// The server scopes the edit to the authenticated token (never the body), so
  /// a fan only ever edits their own profile; nickname is the sole display PII
  /// (already stored) so no new PII is introduced. The 1–40 length is validated
  /// client-side before this is called and re-enforced by the server. Returns
  /// the refreshed [FanMe]. A 401 — or a 403, which the `/api/fan/me` PATCH only
  /// ever returns for a missing/expired session (it has no owner-scoped 403) —
  /// becomes a [SettingsAuthRequiredException] so a session expiring mid-edit
  /// drops to the login-required state instead of a stale generic error.
  Future<FanMe> updateNickname(String nickname) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/fan/me',
        data: <String, dynamic>{'nickname': nickname},
      );
      return FanMe.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 401 || statusCode == 403) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [SettingsRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the screen can render a mock
/// profile (or the 401 branch) and exercise the nickname edit offline.
final settingsRepositoryProvider = Provider<SettingsRepository>(
  (ref) => SettingsRepository(ref.watch(dioProvider)),
);
