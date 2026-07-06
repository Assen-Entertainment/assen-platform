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

/// The validated connection settings the HTTP client is built from.
///
/// Constructing this in a release build with no `ASSEN_API_BASE_URL` define
/// throws (empty base URL → [ArgumentError]), surfacing the misconfiguration at
/// startup rather than as silent request failures.
final apiClientConfigProvider = Provider<ApiClientConfig>(
  (ref) => ApiClientConfig(baseUrl: _resolveBaseUrl()),
);

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
  dio.interceptors.add(AuthInterceptor(ref));
  return dio;
});

/// Attaches the opaque access token to requests and marks the refresh-rotation
/// point on 401.
///
/// The token is read from [authControllerProvider]; signed out, no header is
/// added (public endpoints still resolve). TODO(assen): on a 401, call the
/// refresh endpoint, rotate the stored token, and retry the request once (E6
/// gate — needs secure storage + the refresh contract).
class AuthInterceptor extends Interceptor {
  /// Creates an interceptor reading auth state from [_ref].
  AuthInterceptor(this._ref);

  final Ref _ref;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _ref.read(authControllerProvider).accessToken;
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // TODO(assen): refresh-token rotation point — swap the expired token and
    // replay the request once before surfacing the error (E6 gate).
    handler.next(err);
  }
}
