import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The machine-readable reason an auth call failed.
///
/// Mirrors the server `ErrorCode` values the fan surface returns (see
/// `config/errors.py`). The UI branches on the reason — never on the localized
/// `detail` copy — so, e.g., a login can route an unregistered number to the
/// signup step while a wrong code re-prompts the OTP field.
enum AuthFailureReason {
  /// The phone verified but holds no active fan account → guide to signup
  /// (`AccountNotRegistered`).
  accountNotRegistered,

  /// The OTP code was wrong/expired (`OtpInvalid`).
  invalidOtp,

  /// The phone number was malformed (`PhoneInvalid`).
  invalidPhone,

  /// A required consent was not granted (`ConsentRequired`).
  consentRequired,

  /// OTP send/verify is not wired on the server (`OtpUnavailable`, 503).
  unavailable,

  /// A network/transport failure, or any unclassified server error.
  unknown,
}

/// A typed auth failure the login/signup UI can branch on.
///
/// Carries only a [reason] and a user-safe [message]; never any token material
/// or request/response body (which could hold a phone number). Deliberately not
/// an `Error` — it is an expected control-flow outcome (wrong code, new user).
class AuthException implements Exception {
  /// Creates an auth failure of [reason] with a display [message].
  const AuthException(this.reason, this.message);

  /// The machine-readable reason (the UI branches on this).
  final AuthFailureReason reason;

  /// A user-facing, PII-free message.
  final String message;

  @override
  String toString() => 'AuthException($reason)';
}

/// The fan authentication API over [Dio] (`/api/fan/*`, ADR-0002 body surface).
///
/// Owns the OTP/login/signup/refresh/logout endpoints and maps the server's
/// coded errors into a typed [AuthException]. The mobile surface always sends
/// `web: false`, so tokens arrive in the JSON body (never cookies) and are
/// handed to the [TokenStore] by the caller — this layer never persists or logs
/// them. When the generated `api_client` (P6) lands, this delegates to it.
class AuthApi {
  /// Creates an API bound to [_dio].
  const AuthApi(this._dio);

  final Dio _dio;

  /// Sends a (mock) signup/login OTP to [phone] (`POST /fan/signup/otp`).
  ///
  /// Returns on a bare ack; the code is never in the response. A malformed
  /// number (422) or an unwired sender (503) surfaces as an [AuthException].
  Future<void> requestOtp(String phone) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/api/fan/signup/otp',
        data: <String, dynamic>{'phone': phone},
      );
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Re-authenticates an existing fan (`POST /fan/login`) and returns the pair.
  ///
  /// An unregistered number raises [AuthFailureReason.accountNotRegistered] so
  /// the UI can offer signup; a wrong code raises
  /// [AuthFailureReason.invalidOtp].
  Future<AuthTokens> login({
    required String phone,
    required String otp,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/login',
        data: <String, dynamic>{
          'phone': phone,
          'otp_code': otp,
          'web': false,
        },
      );
      return _tokensFrom(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Registers a new fan (`POST /fan/signup`) and returns the issued pair.
  ///
  /// [consentTerms]/[consentPrivacy] are the required 약관 grants captured on the
  /// signup step; the server records the consent fact + version, never PII.
  Future<AuthTokens> signup({
    required String phone,
    required String otp,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/signup',
        data: <String, dynamic>{
          'phone': phone,
          'otp_code': otp,
          'nickname': nickname,
          'consent_terms': consentTerms,
          'consent_privacy': consentPrivacy,
          'web': false,
        },
      );
      return _tokensFrom(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Rotates [refreshToken] for a fresh pair (`POST /fan/refresh`).
  ///
  /// Lets a [DioException] propagate (the caller — the auth controller's
  /// single-flight refresh — treats any failure as a dead family and signs out)
  /// rather than wrapping it, since there is no user-facing branch here.
  Future<AuthTokens> refresh(String refreshToken) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/fan/refresh',
      data: <String, dynamic>{'refresh_token': refreshToken},
    );
    return _tokensFrom(response.data);
  }

  /// Best-effort session teardown (`POST /fan/logout`).
  ///
  /// Sends the current [accessToken] (when present) as the bearer so the server
  /// can revoke the whole token family; the endpoint is idempotent and clearing
  /// the local session does not depend on this succeeding.
  Future<void> logout(String? accessToken) async {
    await _dio.post<Map<String, dynamic>>(
      '/api/fan/logout',
      options: accessToken == null
          ? null
          : Options(headers: {'Authorization': 'Bearer $accessToken'}),
    );
  }

  /// Parses a `SignupOut` body into an [AuthTokens] pair.
  ///
  /// The mobile (`web: false`) surface always carries the tokens in the body; a
  /// response missing them is a contract violation and throws.
  AuthTokens _tokensFrom(Map<String, dynamic>? data) {
    final access = data?['access_token'];
    final refresh = data?['refresh_token'];
    if (access is! String ||
        access.isEmpty ||
        refresh is! String ||
        refresh.isEmpty) {
      throw const AuthException(
        AuthFailureReason.unknown,
        '로그인에 실패했어요. 잠시 후 다시 시도해 주세요.',
      );
    }
    return AuthTokens(accessToken: access, refreshToken: refresh);
  }

  /// Maps a [DioException] to a typed [AuthException] by the server error code.
  ///
  /// Only the stable `code` is read (never the number-bearing request body), so
  /// no PII is captured into the failure.
  AuthException _mapError(DioException error) {
    final data = error.response?.data;
    final code = data is Map ? data['code'] as String? : null;
    switch (code) {
      case 'AccountNotRegistered':
        return const AuthException(
          AuthFailureReason.accountNotRegistered,
          '가입이 필요해요. 계속해서 회원가입을 진행해 주세요.',
        );
      case 'OtpInvalid':
        return const AuthException(
          AuthFailureReason.invalidOtp,
          '인증번호가 올바르지 않아요.',
        );
      case 'PhoneInvalid':
        return const AuthException(
          AuthFailureReason.invalidPhone,
          '올바른 휴대폰 번호를 입력해 주세요.',
        );
      case 'ConsentRequired':
        return const AuthException(
          AuthFailureReason.consentRequired,
          '필수 약관에 동의해 주세요.',
        );
      case 'OtpUnavailable':
        return const AuthException(
          AuthFailureReason.unavailable,
          '인증 서비스를 잠시 사용할 수 없어요. 잠시 후 다시 시도해 주세요.',
        );
      default:
        return const AuthException(
          AuthFailureReason.unknown,
          '문제가 발생했어요. 네트워크 상태를 확인하고 다시 시도해 주세요.',
        );
    }
  }
}

/// Provides the [AuthApi] on its own un-intercepted [Dio].
///
/// Deliberately NOT the shared [dioProvider]: the auth endpoints must not run
/// through the [AuthInterceptor], both to avoid a refresh-on-refresh recursion
/// and to break the provider cycle (the interceptor rotates via this API). It
/// reuses the same validated base URL. Overridden with a fake in tests so the
/// auth controller/login screen can be exercised without a network.
final authApiProvider = Provider<AuthApi>((ref) {
  final config = ref.watch(apiClientConfigProvider);
  return AuthApi(
    Dio(
      BaseOptions(
        baseUrl: config.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ),
    ),
  );
});
