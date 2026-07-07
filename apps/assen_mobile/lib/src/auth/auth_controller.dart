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
    try {
      final tokens = await ref.read(tokenStoreProvider).read();
      if (tokens != null) {
        state = AuthState(
          isAuthenticated: true,
          accessToken: tokens.accessToken,
        );
      }
    } on Object {
      // Secure storage unavailable or unreadable: remain signed out.
      state = const AuthState.unauthenticated();
    }
  }

  /// Sends a signup/login OTP to [phone] (`POST /fan/signup/otp`).
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
    await ref.read(tokenStoreProvider).save(tokens);
    state = AuthState(isAuthenticated: true, accessToken: tokens.accessToken);
  }

  /// Rotates the refresh token, returning the fresh access token or null.
  ///
  /// Single-flight: concurrent callers (a burst of 401s) share one in-flight
  /// rotation so only one `POST /fan/refresh` is sent; the rest await its
  /// result. A null result means the family is dead and the session has been
  /// cleared — the interceptor then surfaces the original 401. Called by the
  /// API auth interceptor; not for direct UI use.
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
  Future<String?> _rotate() async {
    final refreshToken =
        (await ref.read(tokenStoreProvider).read())?.refreshToken;
    if (refreshToken == null || refreshToken.isEmpty) {
      await _clearSession();
      return null;
    }
    try {
      final next = await ref.read(authApiProvider).refresh(refreshToken);
      await ref.read(tokenStoreProvider).save(next);
      state = AuthState(isAuthenticated: true, accessToken: next.accessToken);
      return next.accessToken;
    } on DioException {
      // Rotation was rejected (expired/revoked/reused → 401): the whole family
      // is dead, so drop the session and forget the stored tokens.
      await _clearSession();
      return null;
    }
  }

  /// Signs out: clears the session immediately, then revokes server-side and
  /// forgets the stored tokens in the background.
  ///
  /// The local state flips synchronously so the router releases the auth-gated
  /// tabs at once; the network revoke is best-effort.
  void signOut() {
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
