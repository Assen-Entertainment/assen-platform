import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The machine-readable reason an auth call failed.
///
/// Mirrors the server `ErrorCode` values the fan surface returns (see
/// `config/errors.py`). The UI branches on the reason — never on the localized
/// `detail` copy — so, e.g., an unverified account can be told to open its
/// verification mail while a wrong password re-prompts the credentials.
enum AuthFailureReason {
  /// The email already backs a verified account (`EmailAlreadyRegistered`,
  /// 409) → guide to login.
  emailAlreadyRegistered,

  /// The password was right but the address was never confirmed
  /// (`EmailNotVerified`, 403) → guide back to the verification mail.
  emailNotVerified,

  /// Login was refused (`InvalidCredentials`, 422). Disclosure-safe: a wrong
  /// email and a wrong password are deliberately indistinguishable. Also
  /// raised by signup when the password is under the 8-character floor.
  invalidCredentials,

  /// The verification token was forged, malformed, or expired
  /// (`EmailVerificationInvalid`, 400).
  emailVerificationInvalid,

  /// A required consent was not granted (`ConsentRequired`).
  consentRequired,

  /// Signup was attempted without confirming the 만 14세 이상 floor
  /// (`Underage`).
  underage,

  /// The email surface is not wired on the server (`EmailUnavailable`, 503).
  unavailable,

  /// A network/transport failure, or any unclassified server error.
  unknown,
}

/// A typed auth failure the login/signup UI can branch on.
///
/// Carries only a [reason] and a user-safe [message]; never any token material
/// or request/response body (which could hold an email address or password).
/// Deliberately not an `Error` — it is an expected control-flow outcome (wrong
/// password, unverified account).
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
/// Owns the email signup/verify/login/refresh/logout endpoints and maps the
/// server's coded errors into a typed [AuthException]. The mobile surface
/// always sends `web: false`, so tokens arrive in the JSON body (never cookies)
/// and are handed to the [TokenStore] by the caller — this layer never persists
/// or logs them. Social login (kakao/google/naver) needs OAuth deep links +
/// provider redirect-URI registration and is a later wave. When the generated
/// `api_client` (P6) lands, this delegates to it.
class AuthApi {
  /// Creates an API bound to [_dio].
  const AuthApi(this._dio);

  final Dio _dio;

  /// Authenticates an existing fan (`POST /fan/login/email`) and returns the
  /// issued pair.
  ///
  /// A wrong address and a wrong password are indistinguishable by design
  /// ([AuthFailureReason.invalidCredentials]); an account that never confirmed
  /// its verification mail raises [AuthFailureReason.emailNotVerified].
  Future<AuthTokens> loginEmail({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/login/email',
        data: <String, dynamic>{
          'email': email,
          'password': password,
          'web': false,
        },
      );
      return _tokensFrom(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Registers an (unverified) fan (`POST /fan/signup/email`) and returns the
  /// verification token.
  ///
  /// No session is issued here — the fan confirms the emailed link first (see
  /// [verifyEmail]), so this endpoint takes no `web` surface flag. The returned
  /// token is non-empty ONLY under the server's dev/test
  /// `EMAIL_VERIFY_RETURN_TOKEN` flag (so QA can complete without an inbox);
  /// on any real surface it is `""`.
  ///
  /// [consentTerms]/[consentPrivacy]/[ageOver14] are the required grants
  /// captured on the signup step; the server records the consent fact +
  /// version, never PII.
  Future<String> signupEmail({
    required String email,
    required String password,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
    required bool ageOver14,
    bool marketingConsent = false,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/signup/email',
        data: <String, dynamic>{
          'email': email,
          'password': password,
          'nickname': nickname,
          'consent_terms': consentTerms,
          'consent_privacy': consentPrivacy,
          'age_over_14': ageOver14,
          'marketing_consent': marketingConsent,
        },
      );
      final token = response.data?['verification_token'];
      return token is String ? token : '';
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Confirms an email-verification [token] (`POST /fan/verify-email`) and
  /// returns the issued pair.
  ///
  /// The first valid confirm marks the account verified and logs it in; a
  /// forged/expired token raises [AuthFailureReason.emailVerificationInvalid].
  Future<AuthTokens> verifyEmail(String token) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/fan/verify-email',
        data: <String, dynamic>{'token': token, 'web': false},
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
  /// Only the stable `code` is read (never the email-bearing request body), so
  /// no PII is captured into the failure.
  AuthException _mapError(DioException error) {
    final data = error.response?.data;
    final code = data is Map ? data['code'] as String? : null;
    switch (code) {
      case 'EmailAlreadyRegistered':
        return const AuthException(
          AuthFailureReason.emailAlreadyRegistered,
          '이미 가입된 이메일이에요. 로그인해 주세요.',
        );
      case 'EmailNotVerified':
        return const AuthException(
          AuthFailureReason.emailNotVerified,
          '이메일 인증이 필요해요. 받은 메일의 링크로 인증을 완료해 주세요.',
        );
      case 'InvalidCredentials':
        return const AuthException(
          AuthFailureReason.invalidCredentials,
          '이메일 또는 비밀번호가 올바르지 않아요.',
        );
      case 'EmailVerificationInvalid':
        return const AuthException(
          AuthFailureReason.emailVerificationInvalid,
          '인증 링크가 유효하지 않거나 만료됐어요. 다시 시도해 주세요.',
        );
      case 'ConsentRequired':
        return const AuthException(
          AuthFailureReason.consentRequired,
          '필수 약관에 동의해 주세요.',
        );
      case 'Underage':
        return const AuthException(
          AuthFailureReason.underage,
          '만 14세 이상만 가입할 수 있어요.',
        );
      case 'EmailUnavailable':
        return const AuthException(
          AuthFailureReason.unavailable,
          '이메일 서비스를 잠시 사용할 수 없어요. 잠시 후 다시 시도해 주세요.',
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
