import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/settings/marketing_consent.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Reads and updates the signed-in fan's per-channel marketing opt-in.
///
/// A thin repository over [Dio] owning `/api/fan/marketing` (GET read, PUT save)
/// and the JSON↔model mapping so the controller/UI stay transport-agnostic. A
/// 401/403 becomes a [SettingsAuthRequiredException] so the 알림 설정 screen drops
/// to the shared "로그인이 필요해요" state; other transport errors propagate. When the
/// generated `api_client` (P6) lands this delegates to it instead of Dio.
class MarketingRepository {
  /// Creates a repository backed by [_dio].
  const MarketingRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's consent via `GET /api/fan/marketing` (auth required).
  Future<MarketingConsent> fetchConsent() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/fan/marketing',
      );
      return MarketingConsent.fromJson(
        response.data ?? const <String, dynamic>{},
      );
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401 || status == 403) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }

  /// Saves the full per-channel consent via `PUT /api/fan/marketing`.
  ///
  /// The server writes all three channels from one payload (each change appends
  /// a durable ConsentRecord audit row), so the caller sends the complete
  /// desired state — not a delta. Returns the server-confirmed state so the
  /// toggle reconciles against what actually persisted.
  Future<MarketingConsent> saveConsent(MarketingConsent consent) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/api/fan/marketing',
        data: consent.toJson(),
      );
      return MarketingConsent.fromJson(
        response.data ?? const <String, dynamic>{},
      );
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401 || status == 403) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [MarketingRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the 알림 설정 screen can render mock
/// consent (or the 401 branch) and exercise the toggle save offline.
final marketingRepositoryProvider = Provider<MarketingRepository>(
  (ref) => MarketingRepository(ref.watch(dioProvider)),
);
