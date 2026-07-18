// Unit tests for the auth controller: email login starting a persisted session,
// a bad password surfacing a typed error, signup issuing no session until the
// emailed link is verified, verify-email starting the session, single-flight
// refresh rotation, a failed rotation clearing the session, and sign-out
// clearing stored tokens. R14 race hardening: a sign-out beats an in-flight
// refresh, and a non-Dio rotation failure (store throw / malformed refresh)
// still fails closed. Backed by an in-memory token store and a fake auth API —
// no network, no platform channel.

import 'dart:async';

import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// An in-memory [TokenStore] recording clears, so persistence can be asserted.
///
/// [failRead]/[failSave] make the corresponding op throw a non-Dio error, to
/// exercise the controller's fail-closed rotation path.
class _InMemoryTokenStore implements TokenStore {
  _InMemoryTokenStore([this.tokens]);

  AuthTokens? tokens;
  int clearCount = 0;
  bool failRead = false;
  bool failSave = false;

  @override
  Future<AuthTokens?> read() async {
    if (failRead) throw StateError('secure storage read failed');
    return tokens;
  }

  @override
  Future<void> save(AuthTokens value) async {
    if (failSave) throw StateError('secure storage write failed');
    tokens = value;
  }

  @override
  Future<void> clear() async {
    tokens = null;
    clearCount++;
  }
}

/// A fake [AuthApi] with scriptable outcomes and call counters.
///
/// [refreshGate], when set, holds the rotation open until the test completes it
/// (to interleave a [AuthController.signOut] with an in-flight refresh).
/// [malformedRefresh] makes the rotation throw a non-Dio [AuthException] (as
/// the real API does on a bad body), to prove fail-closed on any exception.
class _FakeAuthApi implements AuthApi {
  _FakeAuthApi({
    this.loginError,
    this.refreshFails = false,
    this.refreshGate,
    this.malformedRefresh = false,
  });

  final AuthException? loginError;
  final bool refreshFails;
  final Completer<void>? refreshGate;
  final bool malformedRefresh;

  int signupCount = 0;
  int refreshCount = 0;
  int logoutCount = 0;

  static const AuthTokens _issued = AuthTokens(
    accessToken: 'access-1',
    refreshToken: 'refresh-1',
  );

  /// The token a dev/test server echoes back from signup.
  static const String devVerificationToken = 'verify-token-1';

  @override
  Future<AuthTokens> loginEmail({
    required String email,
    required String password,
  }) async {
    final error = loginError;
    if (error != null) throw error;
    return _issued;
  }

  @override
  Future<String> signupEmail({
    required String email,
    required String password,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
    required bool ageOver14,
    bool marketingConsent = false,
  }) async {
    signupCount++;
    return devVerificationToken;
  }

  @override
  Future<AuthTokens> verifyEmail(String token) async => _issued;

  @override
  Future<AuthTokens> refresh(String refreshToken) async {
    refreshCount++;
    final gate = refreshGate;
    if (gate != null) await gate.future;
    if (malformedRefresh) {
      // The real API throws a typed (non-Dio) AuthException on a bad body.
      throw const AuthException(
        AuthFailureReason.unknown,
        '로그인에 실패했어요. 잠시 후 다시 시도해 주세요.',
      );
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
    return const AuthTokens(accessToken: 'access-2', refreshToken: 'refresh-2');
  }

  @override
  Future<void> logout(String? accessToken) async => logoutCount++;
}

ProviderContainer _container(_FakeAuthApi api, _InMemoryTokenStore store) {
  final container = ProviderContainer(
    overrides: [
      authApiProvider.overrideWithValue(api),
      tokenStoreProvider.overrideWithValue(store),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

/// Lets the controller's async startup restore settle.
Future<void> _settle() => Future<void>.delayed(Duration.zero);

void main() {
  test('email login persists the token pair and authenticates', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore();
    final container = _container(api, store);

    await container
        .read(authControllerProvider.notifier)
        .loginEmail(email: 'fan@assen.test', password: 'hunter2hunter2');

    final state = container.read(authControllerProvider);
    expect(state.isAuthenticated, isTrue);
    expect(state.accessToken, 'access-1');
    expect(store.tokens?.refreshToken, 'refresh-1');
  });

  test('a bad credential login throws and stays signed out', () async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.invalidCredentials,
        '이메일 또는 비밀번호가 올바르지 않아요.',
      ),
    );
    final store = _InMemoryTokenStore();
    final container = _container(api, store);

    await expectLater(
      container
          .read(authControllerProvider.notifier)
          .loginEmail(email: 'fan@assen.test', password: 'wrong-password'),
      throwsA(
        isA<AuthException>().having(
          (e) => e.reason,
          'reason',
          AuthFailureReason.invalidCredentials,
        ),
      ),
    );
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
  });

  test('an unverified login throws emailNotVerified', () async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.emailNotVerified,
        '이메일 인증이 필요해요.',
      ),
    );
    final container = _container(api, _InMemoryTokenStore());

    await expectLater(
      container
          .read(authControllerProvider.notifier)
          .loginEmail(email: 'fan@assen.test', password: 'hunter2hunter2'),
      throwsA(
        isA<AuthException>().having(
          (e) => e.reason,
          'reason',
          AuthFailureReason.emailNotVerified,
        ),
      ),
    );
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
  });

  test('signup issues no session and returns the verification token', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore();
    final container = _container(api, store);

    final token = await container
        .read(authControllerProvider.notifier)
        .signupEmail(
          email: 'fan@assen.test',
          password: 'hunter2hunter2',
          nickname: '민지',
          consentTerms: true,
          consentPrivacy: true,
          ageOver14: true,
        );

    expect(token, _FakeAuthApi.devVerificationToken);
    expect(api.signupCount, 1);
    // The server issues no tokens until the emailed link is confirmed, so the
    // session must stay signed out and nothing may be persisted.
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
  });

  test('verifyEmail persists the pair and authenticates', () async {
    final store = _InMemoryTokenStore();
    final container = _container(_FakeAuthApi(), store);

    await container
        .read(authControllerProvider.notifier)
        .verifyEmail(_FakeAuthApi.devVerificationToken);

    expect(container.read(authControllerProvider).isAuthenticated, isTrue);
    expect(store.tokens?.accessToken, 'access-1');
  });

  test('a stored session is restored on startup', () async {
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'saved', refreshToken: 'saved-r'),
    );
    // build() returns signed-out synchronously; restore flips it after read().
    final container = _container(_FakeAuthApi(), store)
      ..read(authControllerProvider.notifier);
    await _settle();

    final state = container.read(authControllerProvider);
    expect(state.isAuthenticated, isTrue);
    expect(state.accessToken, 'saved');
  });

  test('concurrent refreshes collapse to one rotation', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);

    final first = controller.refreshSession();
    final second = controller.refreshSession();
    final results = await Future.wait([first, second]);

    expect(identical(first, second), isTrue);
    expect(api.refreshCount, 1);
    expect(results, ['access-2', 'access-2']);
    expect(store.tokens?.accessToken, 'access-2');
  });

  test('a failed rotation clears the session and returns null', () async {
    final api = _FakeAuthApi(refreshFails: true);
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);
    await _settle();

    final token = await controller.refreshSession();

    expect(token, isNull);
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
  });

  test('signOut clears the session, tokens, and revokes server-side', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore();
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);

    await controller.loginEmail(
      email: 'fan@assen.test',
      password: 'hunter2hunter2',
    );
    controller.signOut();
    // Let the best-effort revoke + storage clear run.
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
    expect(store.clearCount, greaterThanOrEqualTo(1));
    expect(api.logoutCount, 1);
  });

  test('sign-out beats an in-flight refresh (no revival)', () async {
    // The rotation is held open (gate) while the user signs out; when it later
    // completes with fresh tokens the epoch has moved, so it must be discarded
    // — the session stays signed out and no fresh tokens are persisted.
    final gate = Completer<void>();
    final api = _FakeAuthApi(refreshGate: gate);
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);
    await _settle();

    final rotation = controller.refreshSession();
    await _settle(); // let _rotate reach the held refresh call
    controller.signOut(); // bumps the epoch, clears the session
    gate.complete(); // the refresh now resolves with fresh tokens
    final token = await rotation;
    // Let sign-out's best-effort revoke + storage clear run.
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(token, isNull); // the stale rotation was discarded
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull); // no revival save; sign-out's clear stands
    expect(api.refreshCount, 1); // the refresh ran once and was thrown away
  });

  test('a malformed refresh fails closed (non-Dio error)', () async {
    final api = _FakeAuthApi(malformedRefresh: true);
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);
    await _settle();

    // Must resolve to null (fail-closed), never rethrow the AuthException.
    final token = await controller.refreshSession();

    expect(token, isNull);
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
  });

  test('a storage read failure during rotation fails closed', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);
    await _settle();
    expect(container.read(authControllerProvider).isAuthenticated, isTrue);

    store.failRead = true; // the rotation's store read now throws
    final token = await controller.refreshSession();

    expect(token, isNull);
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(api.refreshCount, 0); // never reached the network on a store failure
  });

  test('a storage save failure during rotation fails closed', () async {
    final api = _FakeAuthApi();
    final store = _InMemoryTokenStore(
      const AuthTokens(accessToken: 'access-1', refreshToken: 'refresh-1'),
    );
    final container = _container(api, store);
    final controller = container.read(authControllerProvider.notifier);
    await _settle();

    store.failSave = true; // persisting the fresh pair now throws
    final token = await controller.refreshSession();

    expect(token, isNull);
    expect(container.read(authControllerProvider).isAuthenticated, isFalse);
    expect(store.tokens, isNull);
  });
}
