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

/// Thrown when the (mock) 본인인증 verifier is not wired on the server (503).
///
/// A typed marker so the 설정 screen shows a "준비 중" notice for the KYC action
/// rather than a generic failure — mirrors the server's fail-closed
/// `KYC_UNAVAILABLE`.
class KycUnavailableException implements Exception {
  /// Creates the KYC-unavailable marker.
  const KycUnavailableException();

  @override
  String toString() => 'KycUnavailableException';
}

/// The derived 인증 flags from confirming (mock) 본인인증 (`VerifyConfirmOut`).
///
/// Carries only the two server-derived flags — never PII (주민번호/생년월일 are
/// never sent to or received from the mock).
class VerifyResult {
  /// Creates a verify result.
  const VerifyResult({required this.adultVerified, required this.kycStatus});

  /// Builds a result from a `VerifyConfirmOut` JSON object.
  factory VerifyResult.fromJson(Map<String, dynamic> json) => VerifyResult(
    adultVerified: json['adult_verified'] as bool? ?? false,
    kycStatus: json['kyc_status'] as String? ?? 'unverified',
  );

  /// Whether the account passed 19+ 본인인증 (derived flag, not PII).
  final bool adultVerified;

  /// The KYC status string (server `kyc_status`).
  final String kycStatus;
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

  /// Runs the (mock) 성인/본인 인증 flow: `POST /verify/start` then
  /// `POST /verify/confirm`, returning the derived flags.
  ///
  /// The mock is deterministic and handles no PII (no 주민번호/생년월일 crosses the
  /// wire) — only the derived `adult_verified` / `kyc_status` come back. A
  /// 401/403 (session expired) becomes a [SettingsAuthRequiredException]; a 503
  /// (verifier unwired) becomes a [KycUnavailableException] so the screen can
  /// explain it.
  Future<VerifyResult> verifyAdult() async {
    try {
      await _dio.post<Map<String, dynamic>>('/api/fan/verify/start');
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/verify/confirm',
      );
      return VerifyResult.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 401 || statusCode == 403) {
        throw const SettingsAuthRequiredException();
      }
      if (statusCode == 503) {
        throw const KycUnavailableException();
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
