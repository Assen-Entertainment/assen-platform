// App-level API handshake smoke (ASS-294): proves the Riverpod-composed HTTP
// client — `dioProvider` built over `apiClientConfigProvider` — actually
// targets the *resolved* base URL, dispatching a GET to `<baseUrl>/<path>`,
// without a real backend. A fake Dio adapter answers in-process (CONSTRAINTS
// #24: offline, deterministic), so this is a plain `flutter test` that runs in
// the ubuntu `flutter` CI job's `melos run test` — no device, no macOS runner.
//
// This closes the "live API handshake" sub-part of ASS-294 at the
// client-contract level (does the app compose a client that talks to the
// configured host?). A full end-to-end handshake against a running server is
// still deferred: it needs CI backend wiring (boot the Django stack + a seeded
// `/api/health`-style endpoint) which is out of scope for the mobile job.

import 'dart:convert';
import 'dart:typed_data';

import 'package:api_client/api_client.dart';
import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A signed-out [TokenStore]: the startup restore reads null, so no request
/// carries an Authorization header and nothing touches the secure-storage
/// platform channel (which has no binding under `flutter test`).
class _SignedOutTokenStore implements TokenStore {
  @override
  Future<AuthTokens?> read() async => null;

  @override
  Future<void> save(AuthTokens tokens) async {}

  @override
  Future<void> clear() async {}
}

/// Records the last request Dio dispatched and answers every call with a fixed
/// 200 JSON body, standing in for the backend so the request path runs to the
/// wire boundary without a socket.
class _CapturingAdapter implements HttpClientAdapter {
  RequestOptions? lastRequest;
  int calls = 0;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls++;
    lastRequest = options;
    return ResponseBody.fromString(
      jsonEncode({'status': 'ok'}),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Future<void> _settle() => Future<void>.delayed(Duration.zero);

/// Wires a container with the real api providers + a signed-out store, reads
/// the composed [Dio], and installs [adapter] so its dispatched requests are
/// captured. Passing [configuredBaseUrl] overrides [apiClientConfigProvider] so
/// a test can pin the resolved base URL the client should target.
Future<(ProviderContainer, Dio)> _wire(
  _CapturingAdapter adapter, {
  String? configuredBaseUrl,
}) async {
  final container = ProviderContainer(
    overrides: [
      tokenStoreProvider.overrideWithValue(_SignedOutTokenStore()),
      if (configuredBaseUrl != null)
        apiClientConfigProvider.overrideWithValue(
          ApiClientConfig(baseUrl: configuredBaseUrl),
        ),
    ],
  );
  addTearDown(container.dispose);
  // Trigger the unawaited startup restore and let it settle to a stable
  // signed-out state before any request goes out.
  container.read(authControllerProvider);
  await _settle();
  final dio = container.read(dioProvider)..httpClientAdapter = adapter;
  return (container, dio);
}

void main() {
  test(
    'the composed client targets the resolved base URL (debug/test default)',
    () async {
      final adapter = _CapturingAdapter();
      final (container, dio) = await _wire(adapter);

      final baseUrl = container.read(apiClientConfigProvider).baseUrl;
      // A debug/test build with no --dart-define falls back to the local dev
      // server — the value the release build-time assertion protects.
      expect(baseUrl, 'http://localhost:8000');
      // The Dio the providers compose points at exactly that base URL, with the
      // connect/receive timeouts wired in (the composed client's shape).
      expect(dio.options.baseUrl, baseUrl);
      expect(dio.options.connectTimeout, const Duration(seconds: 10));
      expect(dio.options.receiveTimeout, const Duration(seconds: 10));

      final response = await dio.get<Map<String, dynamic>>('/api/health');

      // Exactly one GET was dispatched to `<baseUrl>/<path>` and reached the
      // adapter: the app can talk to the configured API.
      expect(response.statusCode, 200);
      expect(adapter.calls, 1);
      expect(adapter.lastRequest?.method, 'GET');
      expect(adapter.lastRequest?.uri.toString(), '$baseUrl/api/health');
      // Signed out: a public request carries no bearer header.
      expect(
        adapter.lastRequest?.headers.containsKey('Authorization'),
        isFalse,
      );
    },
  );

  test(
    'a configured base URL flows through to the dispatched request',
    () async {
      const configured = 'https://api.assen.test';
      final adapter = _CapturingAdapter();
      final (_, dio) = await _wire(adapter, configuredBaseUrl: configured);

      expect(dio.options.baseUrl, configured);

      await dio.get<Map<String, dynamic>>('/api/fan/me');

      // Whatever base URL is configured at build time governs where every
      // request is sent — the handshake targets the resolved host, not a
      // hard-coded default.
      expect(adapter.lastRequest?.uri.toString(), '$configured/api/fan/me');
    },
  );
}
