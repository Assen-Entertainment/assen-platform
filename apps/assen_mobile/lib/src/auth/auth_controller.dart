import 'dart:async';

import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Immutable authentication state for the session.
///
/// Holds whether a viewer is signed in and, if so, the opaque access token used
/// to authorize API calls. The token is the short-lived bearer; its long-lived
/// refresh counterpart lives only in secure storage (see [TokenStore]) and is
/// used by [AuthController.refreshSession] on a 401.
@immutable
class AuthState {
  /// Creates an auth state.
  const AuthState({required this.isAuthenticated, this.accessToken});

  /// The signed-out default: guests may browse public tabs.
  const AuthState.unauthenticated()
    : isAuthenticated = false,
      accessToken = null;

  /// Whether a viewer is signed in.
  final bool isAuthenticated;

  /// The opaque bearer token attached to authorized requests; null when signed
  /// out. Never logged.
  final String? accessToken;
}

/// Owns the session [AuthState] and the token lifecycle (E6 auth, #26).
///
/// On construction it restores any token pair from secure storage (fail-closed
/// on any read error). It exposes the OTP/login/signup/logout flows against the
/// backend `/api/fan/*` surface and a single-flight [refreshSession] the API
/// interceptor calls on a 401. Persisted material is the token pair only —
/// never a phone number or other PII — and tokens are never logged.
class AuthController extends Notifier<AuthState> {
  /// Dedupes concurrent refreshes: while a rotation is in flight every 401
  /// awaits the same future so only one `POST /fan/refresh` is ever sent.
  Future<String?>? _refreshInFlight;

  /// Monotonic session epoch guarding against stale async writes.
  ///
  /// Bumped on every session-identity change — a successful login/signup/
  /// rotation and on [signOut]. Each result-applying flow ([_restore],
  /// [_startSession], [_rotate]) captures this at its start and applies its
  /// result (flip to authenticated / persist tokens) only when the epoch is
  /// still current. A slow in-flight op whose epoch has moved is discarded, so
  /// a late refresh can neither revive a signed-out session nor clobber a
  /// fresher one — in particular, [signOut] always beats an in-flight refresh.
  int _generation = 0;

  @override
  AuthState build() {
    unawaited(_restore());
    return const AuthState.unauthenticated();
  }

  /// Restores a stored session at startup, if any.
  ///
  /// Fail-closed: a missing pair or any storage error (e.g. no platform channel
  /// under `flutter test`) leaves the app signed out. Never surfaces token
  /// material.
  Future<void> _restore() async {
    final generation = _generation;
    try {
      final tokens = await ref.read(tokenStoreProvider).read();
      if (tokens == null) return;
      // A login or sign-out that raced ahead of this restore already owns the
      // session: discard the stale restore rather than overwrite it.
      if (generation != _generation) return;
      state = AuthState(isAuthenticated: true, accessToken: tokens.accessToken);
    } on Object {
      // Secure storage unavailable or unreadable: remain signed out — unless a
      // newer session was established while the read was in flight.
      if (generation == _generation) {
        state = const AuthState.unauthenticated();
      }
    }
  }

  /// Sends a signup/login OTP to [phone] (`POST /fan/signup/otp`).
  ///
  /// DEFERRED (real-SMS hardening): the mock sender issues a deterministic code
  /// that the same phone can reuse across a login attempt and a subsequent
  /// signup. A single-use / step-bound OTP is gated behind the real SMS adapter
  /// (mock disabled in production via `ENABLE_MOCK_FAN_OTP=False`), so this is
  /// not exploitable on a shipped build.
  Future<void> requestOtp(String phone) =>
      ref.read(authApiProvider).requestOtp(phone);

  /// Re-authenticates an existing fan and, on success, starts the session.
  ///
  /// Throws [AuthException] on failure (e.g.
  /// [AuthFailureReason.accountNotRegistered] so the caller can offer signup).
  Future<void> login({required String phone, required String otp}) async {
    final tokens = await ref
        .read(authApiProvider)
        .login(phone: phone, otp: otp);
    await _startSession(tokens);
  }

  /// Registers a new fan (phone + OTP + nickname + consent) and starts the
  /// session on success.
  Future<void> signup({
    required String phone,
    required String otp,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
  }) async {
    final tokens = await ref
        .read(authApiProvider)
        .signup(
          phone: phone,
          otp: otp,
          nickname: nickname,
          consentTerms: consentTerms,
          consentPrivacy: consentPrivacy,
        );
    await _startSession(tokens);
  }

  /// Persists [tokens] and flips the session to authenticated.
  Future<void> _startSession(AuthTokens tokens) async {
    final generation = _generation;
    await ref.read(tokenStoreProvider).save(tokens);
    // A sign-out (or another session) advanced the epoch while persisting:
    // discard so a stale login cannot resurrect a session the user just left.
    if (generation != _generation) return;
    _generation++;
    state = AuthState(isAuthenticated: true, accessToken: tokens.accessToken);
  }

  /// Rotates the refresh token, returning the fresh access token or null.
  ///
  /// Single-flight: concurrent callers (a burst of 401s) share one in-flight
  /// rotation so only one `POST /fan/refresh` is sent; the rest await its
  /// result. A null result means the family is dead and the session has been
  /// cleared — the interceptor then surfaces the original 401. Never throws
  /// (fail-closed: any error resolves to null), so callers never dangle. Called
  /// by the API auth interceptor; not for direct UI use.
  ///
  /// DEFERRED (proactive scheduling): rotation is purely 401-reactive — we do
  /// not parse the access token's expiry to refresh ahead of time. The reactive
  /// path is correct (a request that would 401 triggers exactly one rotation);
  /// a pre-emptive scheduler is a latency optimization only.
  Future<String?> refreshSession() {
    final existing = _refreshInFlight;
    if (existing != null) return existing;
    final future = _rotate();
    _refreshInFlight = future;
    unawaited(
      future.whenComplete(() {
        // Only clear the slot if it still points at this rotation (a later
        // rotation may already have replaced it).
        if (identical(_refreshInFlight, future)) _refreshInFlight = null;
      }),
    );
    return future;
  }

  /// Performs one refresh-token rotation.
  ///
  /// Fail-closed and epoch-guarded. Any failure — a rejected rotation
  /// (expired/revoked/reused → 401), an unreadable/unwritable store, or a
  /// malformed refresh body — drops the session and returns null (never
  /// throws). If the session epoch advanced while the network call was in
  /// flight (a concurrent [signOut] or a newer login), the result is discarded
  /// without touching state or storage, so a stale rotation cannot revive a
  /// signed-out session or overwrite a fresher one.
  Future<String?> _rotate() async {
    final generation = _generation;
    try {
      final refreshToken =
          (await ref.read(tokenStoreProvider).read())?.refreshToken;
      if (refreshToken == null || refreshToken.isEmpty) {
        if (generation == _generation) await _clearSession();
        return null;
      }
      final next = await ref.read(authApiProvider).refresh(refreshToken);
      if (generation != _generation) {
        // A sign-out or newer login superseded this rotation while it was in
        // flight: discard its result. Do NOT clear here — that would wipe the
        // fresher session's tokens.
        return null;
      }
      await ref.read(tokenStoreProvider).save(next);
      _generation++;
      state = AuthState(isAuthenticated: true, accessToken: next.accessToken);
      return next.accessToken;
    } on Object {
      // Fail-closed: the family can no longer be trusted, so drop the session
      // and forget the stored tokens — unless a newer epoch already replaced
      // this one, in which case leave that fresher session intact.
      if (generation == _generation) await _clearSession();
      return null;
    }
  }

  /// Signs out: clears the session immediately, then revokes server-side and
  /// forgets the stored tokens in the background.
  ///
  /// The local state flips synchronously so the router releases the auth-gated
  /// tabs at once; the network revoke is best-effort.
  void signOut() {
    // Advance the epoch first so any refresh already in flight is invalidated:
    // its completion can no longer re-authenticate this now-signed-out session.
    _generation++;
    final token = state.accessToken;
    state = const AuthState.unauthenticated();
    unawaited(_endSession(token));
  }

  /// Best-effort server revoke + storage clear for [signOut].
  Future<void> _endSession(String? accessToken) async {
    try {
      await ref.read(authApiProvider).logout(accessToken);
    } on DioException {
      // The server revoke is best-effort; the stored tokens are cleared below
      // regardless so the device is signed out even when offline.
    }
    await ref.read(tokenStoreProvider).clear();
  }

  /// Drops the in-memory session and forgets the stored tokens.
  Future<void> _clearSession() async {
    state = const AuthState.unauthenticated();
    await ref.read(tokenStoreProvider).clear();
  }
}

/// Exposes the session [AuthState] and its [AuthController].
final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
