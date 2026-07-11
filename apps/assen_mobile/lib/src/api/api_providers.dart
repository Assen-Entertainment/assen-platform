import 'dart:async';

import 'package:api_client/api_client.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The backend base URL supplied at build time
/// (`--dart-define=ASSEN_API_BASE_URL=https://api.assen.example`). Empty when no
/// define is passed.
const String _baseUrlFromEnv = String.fromEnvironment('ASSEN_API_BASE_URL');

/// Resolves the backend base URL, failing fast on a misconfigured release.
///
/// Release builds MUST pass `--dart-define=ASSEN_API_BASE_URL=...`: when the
/// define is empty in a release build the value stays empty so
/// [ApiClientConfig] throws an [ArgumentError] at startup — we never ship a
/// silent placeholder host that would let a broken build launch and quietly
/// fail every request.
/// Debug/profile builds fall back to the local dev server so `flutter run` works
/// with no extra flags (use `http://10.0.2.2:8000` from an Android emulator,
/// which maps to the host machine's localhost).
String _resolveBaseUrl() {
  if (_baseUrlFromEnv.isNotEmpty) return _baseUrlFromEnv;
  return kReleaseMode ? _baseUrlFromEnv : 'http://localhost:8000';
}

/// Fails fast at startup — release builds only — when no API base URL was
/// configured, so a release launched without
/// `--dart-define=ASSEN_API_BASE_URL=...` crashes immediately and
/// deterministically from main rather than lazily on the first request
/// (ASS-294: a release artifact must never launch pointing at nothing). A
/// debug/profile build falls back to the local dev server, so this is a no-op.
void assertApiBaseUrlConfigured() {
  if (kReleaseMode && _baseUrlFromEnv.isEmpty) {
    throw StateError(
      'ASSEN_API_BASE_URL was not provided at build time — a release build '
      'must pass --dart-define=ASSEN_API_BASE_URL=<https URL>.',
    );
  }
}

/// The validated connection settings the HTTP client is built from.
///
/// Constructing this in a release build with no `ASSEN_API_BASE_URL` define
/// throws (empty base URL → [ArgumentError]), surfacing the misconfiguration at
/// startup rather than as silent request failures.
final apiClientConfigProvider = Provider<ApiClientConfig>(
  (ref) => ApiClientConfig(baseUrl: _resolveBaseUrl()),
);

/// A Riverpod retry policy that never retries.
///
/// Passed as the `retry` of the screen controllers so a failed fetch surfaces
/// its error state immediately — the screens offer a manual retry (and a 404/401
/// must not loop) — instead of Riverpod 3.x's default exponential-backoff
/// auto-retry, which would also keep a backoff timer pending.
Duration? noRetry(int retryCount, Object error) => null;

/// The configured [Dio] HTTP client.
///
/// Points at [apiClientConfigProvider]'s base URL and installs the
/// [AuthInterceptor] so authorized requests carry the bearer token — the
/// hand-written glue behind which the generated `api_client` (P6) will sit.
final dioProvider = Provider<Dio>((ref) {
  final config = ref.watch(apiClientConfigProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: config.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ),
  );
  // The interceptor replays a rotated request through this same [dio]; it is
  // handed the instance directly (never `ref.read(dioProvider)`, which would be
  // a self-dependency).
  dio.interceptors.add(AuthInterceptor(ref, dio));
  return dio;
});

/// Attaches the opaque access token to requests and rotates it on a 401.
///
/// The token is read from [authControllerProvider]; signed out, no header is
/// added (public endpoints still resolve). On a 401 for an authorized request
/// it either replays with the current token (when another request has already
/// rotated the token out from under this one — a stale 401) or asks
/// [AuthController.refreshSession] to rotate the refresh token (single-flight —
/// a burst of concurrent 401s shares one rotation) and replays the original
/// request exactly once with the fresh token; a failed rotation clears the
/// session and the original 401 surfaces. Auth endpoints (login/signup/refresh/
/// logout) and an already-retried request are excluded, so a rotation never
/// recurses or loops, and any unexpected error still completes the handler so a
/// request never hangs.
class AuthInterceptor extends Interceptor {
  /// Creates an interceptor reading auth state from [_ref] and replaying a
  /// rotated request through [_dio] (the instance it is installed on).
  AuthInterceptor(this._ref, this._dio);

  final Ref _ref;
  final Dio _dio;

  /// Marks a request already replayed after a rotation, so a second 401 on the
  /// retry surfaces instead of triggering an endless refresh loop.
  static const String _retriedKey = 'assen.auth.retried';

  /// Records the access token this request was actually sent with, so a late
  /// 401 can tell "the token I used is still current" (genuine — rotate) from
  /// "someone already refreshed past my token" (stale — just replay with the
  /// current token, no second rotation).
  static const String _sentTokenKey = 'assen.auth.sent_token';

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _ref.read(authControllerProvider).accessToken;
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
      options.extra[_sentTokenKey] = token;
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final options = err.requestOptions;
    final canRecover =
        err.response?.statusCode == 401 &&
        !_isAuthEndpoint(options.path) &&
        options.extra[_retriedKey] != true;
    if (!canRecover) {
      handler.next(err);
      return;
    }
    unawaited(_rotateAndReplay(err, handler));
  }

  /// Recovers a 401 and replays the failed request exactly once.
  ///
  /// If another in-flight request already rotated the token, this 401 is stale:
  /// replay with the now-current token without a second rotation. Otherwise
  /// rotate once (single-flight) and replay with the fresh token. Every path
  /// completes [handler] exactly once — including on any unexpected error,
  /// where the original 401 is surfaced — so a request can never dangle.
  Future<void> _rotateAndReplay(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final String? token;
    try {
      final sentToken = options.extra[_sentTokenKey];
      final currentToken = _ref.read(authControllerProvider).accessToken;
      if (currentToken != null && currentToken != sentToken) {
        // A concurrent request already refreshed: this 401 raced a completed
        // rotation. Replay with the current token — no redundant rotation.
        token = currentToken;
      } else {
        // The token we sent is still current (or we hold none): rotate once.
        token = await _ref
            .read(authControllerProvider.notifier)
            .refreshSession();
      }
    } on Object {
      // refreshSession is contractually non-throwing, but guard defensively:
      // any failure deciding the replay token surfaces the original 401 rather
      // than leaving the request hung on a handler that never completes.
      handler.next(err);
      return;
    }
    if (token == null) {
      // Rotation failed: the session is already cleared — surface the 401.
      handler.next(err);
      return;
    }
    options
      ..extra[_retriedKey] = true
      ..headers['Authorization'] = 'Bearer $token';
    try {
      handler.resolve(await _dio.fetch<dynamic>(options));
    } on DioException catch (retryError) {
      handler.next(retryError);
    } on Object {
      // A non-Dio replay failure must not hang the request: surface the 401.
      handler.next(err);
    }
  }

  /// Whether [path] is an auth endpoint that must not trigger a rotation-retry
  /// (avoids recursing into `/refresh` and re-driving login/signup/logout).
  bool _isAuthEndpoint(String path) =>
      path.contains('/fan/refresh') ||
      path.contains('/fan/login') ||
      path.contains('/fan/signup') ||
      path.contains('/fan/logout');
}
