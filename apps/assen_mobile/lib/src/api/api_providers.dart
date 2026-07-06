import 'package:api_client/api_client.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The backend base URL, overridable at build time
/// (`--dart-define=ASSEN_API_BASE_URL=...`). The default is a placeholder host
/// so `ApiClientConfig` (which rejects non-absolute URLs) always constructs.
const String _defaultBaseUrl = String.fromEnvironment(
  'ASSEN_API_BASE_URL',
  defaultValue: 'https://api.assen.example',
);

/// The validated connection settings the HTTP client is built from.
final apiClientConfigProvider = Provider<ApiClientConfig>(
  (ref) => ApiClientConfig(baseUrl: _defaultBaseUrl),
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
