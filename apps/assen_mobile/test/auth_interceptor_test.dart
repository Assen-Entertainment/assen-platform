// Integration tests for the Dio AuthInterceptor rotation: a 401 on an
// authorized request rotates the refresh token and replays the request once;
// concurrent 401s share one rotation (single-flight); an already-retried
// request does not loop; and a failed rotation clears the session and surfaces
// the 401. R14 race hardening: a late 401 that carries a pre-rotation token
// replays with the current token without a second rotation; and a non-Dio
// rotation failure still surfaces the original 401 (never hangs). Driven
// through the real dio/AuthController with a fake HTTP adapter and a fake auth
// API — no network, no platform channel.

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// An in-memory [TokenStore] seeded with an (expired) pair.
class _InMemoryTokenStore implements TokenStore {
  _InMemoryTokenStore(this.tokens);

  AuthTokens? tokens;

  @override
  Future<AuthTokens?> read() async => tokens;

  @override
  Future<void> save(AuthTokens value) async => tokens = value;

  @override
  Future<void> clear() async => tokens = null;
}

/// A fake auth API whose refresh swaps the expired token for `Bearer fresh`.
class _FakeAuthApi implements AuthApi {
  _FakeAuthApi({this.refreshFails = false, this.malformedRefresh = false});

  final bool refreshFails;
  final bool malformedRefresh;
  int refreshCount = 0;

  @override
  Future<AuthTokens> refresh(String refreshToken) async {
    refreshCount++;
    // A real async gap so a burst of concurrent 401s all land inside the same
    // in-flight rotation window (proving the controller's single-flight dedup).
    await Future<void>.delayed(const Duration(milliseconds: 20));
    if (malformedRefresh) {
      // A bad refresh body surfaces as a non-Dio AuthException; the controller
      // must still fail closed (null) rather than let it escape.
      throw const AuthException(AuthFailureReason.unknown, 'bad body');
    }
    if (refreshFails) {
      throw DioException(
        requestOptions: RequestOptions(path: '/api/fan/refresh'),
        response: Response<dynamic>(
          requestOptions: RequestOptions(path: '/api/fan/refresh'),
          statusCode: 401,
        ),
      );
    }
    return const AuthTokens(accessToken: 'fresh', refreshToken: 'refresh-2');
  }

  @override
  Future<void> requestOtp(String phone) async {}

  @override
  Future<AuthTokens> login({
    required String phone,
    required String otp,
  }) async => throw UnimplementedError();

  @override
  Future<AuthTokens> signup({
    required String phone,
    required String otp,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
  }) async => throw UnimplementedError();

  @override
  Future<void> logout(String? accessToken) async {}
}

/// A canned HTTP adapter: `Bearer fresh` → 200 fan payload, else → 401.
class _TokenGatedAdapter implements HttpClientAdapter {
  _TokenGatedAdapter({this.always401 = false});

  final bool always401;
  int calls = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls++;
    final authorized =
        !always401 && options.headers['Authorization'] == 'Bearer fresh';
    if (authorized) {
      return ResponseBody.fromString(
        jsonEncode({'id': 'fan-1', 'nickname': '민지', 'role': 'fan'}),
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }
    return ResponseBody.fromString(
      jsonEncode({'detail': 'expired', 'code': 'Unauthorized'}),
      401,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

/// An adapter that lets one request (A, `/me`) drive the rotation to completion
/// while holding a second request (B, `/orders`) whose 401 arrives *after* the
/// rotation, still carrying the pre-rotation token — the late-stale-401 race.
///
/// `Bearer fresh` → 200 on any path. The pre-rotation `expired` token 401s
/// immediately on `/me` (drives the rotation) but is held on `/orders` until
/// [releaseB], then returns a stale 401.
class _StaleReplayAdapter implements HttpClientAdapter {
  final Completer<void> _bReleased = Completer<void>();

  /// Releases B's held 401 (call after A's rotation has completed).
  void releaseB() => _bReleased.complete();

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.headers['Authorization'] == 'Bearer fresh') {
      return ResponseBody.fromString(
        jsonEncode({'id': 'fan-1', 'nickname': '민지', 'role': 'fan'}),
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }
    if (options.path.contains('/orders')) {
      await _bReleased.future; // hold B until A's rotation is done
    }
    return ResponseBody.fromString(
      jsonEncode({'detail': 'expired', 'code': 'Unauthorized'}),
      401,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

Future<void> _settle() => Future<void>.delayed(Duration.zero);

/// Builds a container wired with the real dio/interceptor + fakes, restores the
/// (expired) session, and returns the dio with [adapter] installed.
Future<(ProviderContainer, Dio, _FakeAuthApi)> _wire(
  HttpClientAdapter adapter, {
  bool refreshFails = false,
  bool malformedRefresh = false,
}) async {
  final api = _FakeAuthApi(
    refreshFails: refreshFails,
    malformedRefresh: malformedRefresh,
  );
  final container = ProviderContainer(
    overrides: [
      authApiProvider.overrideWithValue(api),
      tokenStoreProvider.overrideWithValue(
        _InMemoryTokenStore(
          const AuthTokens(accessToken: 'expired', refreshToken: 'refresh-1'),
        ),
      ),
    ],
  );
  addTearDown(container.dispose);
  // Trigger startup restore so the request carries `Bearer expired`.
  container.read(authControllerProvider);
  await _settle();
  final dio = container.read(dioProvider)..httpClientAdapter = adapter;
  return (container, dio, api);
}

void main() {
  test('a 401 rotates the token and replays the request once', () async {
    final adapter = _TokenGatedAdapter();
    final (container, dio, api) = await _wire(adapter);

    final response = await dio.get<Map<String, dynamic>>('/api/fan/me');

    expect(response.statusCode, 200);
    expect(response.data?['nickname'], '민지');
    expect(api.refreshCount, 1);
    expect(container.read(authControllerProvider).accessToken, 'fresh');
  });

  test('concurrent 401s share a single rotation (single-flight)', () async {
    final adapter = _TokenGatedAdapter();
    final (_, dio, api) = await _wire(adapter);

    final responses = await Future.wait([
      dio.get<Map<String, dynamic>>('/api/fan/me'),
      dio.get<Map<String, dynamic>>('/api/fan/orders'),
    ]);

    expect(responses.every((r) => r.statusCode == 200), isTrue);
    expect(api.refreshCount, 1); // one rotation for both 401s
  });

  test('an always-401 endpoint retries once then surfaces (no loop)', () async {
    final adapter = _TokenGatedAdapter(always401: true);
    final (_, dio, api) = await _wire(adapter);

    await expectLater(
      dio.get<Map<String, dynamic>>('/api/fan/me'),
      throwsA(
        isA<DioException>().having(
          (e) => e.response?.statusCode,
          'status',
          401,
        ),
      ),
    );
    // Exactly one rotation: the retry carried the fresh token but still 401'd,
    // and the retried request was not rotated again.
    expect(api.refreshCount, 1);
  });

  test('a failed rotation clears the session and surfaces the 401', () async {
    final adapter = _TokenGatedAdapter(always401: true);
    final (container, dio, _) = await _wire(adapter, refreshFails: true);

    await expectLater(
      dio.get<Map<String, dynamic>>('/api/fan/me'),
      throwsA(isA<DioException>()),
    );
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
  });

  test('a late stale 401 replays without a 2nd rotation', () async {
    final adapter = _StaleReplayAdapter();
    final (container, dio, api) = await _wire(adapter);

    // A and B both go out carrying the pre-rotation `Bearer expired`.
    final aFuture = dio.get<Map<String, dynamic>>('/api/fan/me');
    final bFuture = dio.get<Map<String, dynamic>>('/api/fan/orders');

    // A drives the single rotation to completion; the token is now `fresh`.
    final aResponse = await aFuture;
    expect(aResponse.statusCode, 200);
    expect(api.refreshCount, 1);
    expect(container.read(authControllerProvider).accessToken, 'fresh');

    // Release B's held, now-stale 401: it carried `expired`, so the interceptor
    // replays with the current `fresh` token instead of rotating a second time.
    adapter.releaseB();
    final bResponse = await bFuture;

    expect(bResponse.statusCode, 200);
    expect(api.refreshCount, 1); // still exactly one rotation
  });

  test('a non-Dio rotation failure surfaces the 401 (no hang)', () async {
    final adapter = _TokenGatedAdapter(always401: true);
    final (container, dio, _) = await _wire(adapter, malformedRefresh: true);

    // The malformed refresh throws a non-Dio AuthException inside the rotation;
    // the interceptor must still complete the handler and surface the 401.
    await expectLater(
      dio.get<Map<String, dynamic>>('/api/fan/me'),
      throwsA(isA<DioException>()),
    );
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
  });
}
