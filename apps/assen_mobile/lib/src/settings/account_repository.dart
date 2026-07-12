import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Performs the signed-in fan's account-lifecycle actions (탈퇴).
///
/// Kept separate from [SettingsRepository] (which reads/edits the profile) so
/// the irreversible account mutations have their own seam. A thin repository
/// over [Dio] owning `/api/fan/account/*`; a 401/403 becomes a
/// [SettingsAuthRequiredException] so a caller can treat an already-signed-out
/// state as a benign land-on-login. When the generated `api_client` (P6) lands
/// this delegates to it instead of Dio.
class AccountRepository {
  /// Creates a repository backed by [_dio].
  const AccountRepository(this._dio);

  final Dio _dio;

  /// Withdraws (탈퇴) the account via `POST /api/fan/account/withdraw`.
  ///
  /// The server anonymises the account in place and revokes every token family
  /// (D3, 2026-07-12); the scope is always the authenticated token, so a fan
  /// can only withdraw their own account. Returns nothing on success. A 401/403
  /// (session already gone) becomes a [SettingsAuthRequiredException] so the
  /// caller can treat an already-signed-out state as a benign land-on-login.
  Future<void> withdraw() async {
    try {
      await _dio.post<Map<String, dynamic>>('/api/fan/account/withdraw');
    } on DioException catch (error) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 401 || statusCode == 403) {
        throw const SettingsAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [AccountRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the 계정 관리 screen can exercise
/// 탈퇴 without a network.
final accountRepositoryProvider = Provider<AccountRepository>(
  (ref) => AccountRepository(ref.watch(dioProvider)),
);
