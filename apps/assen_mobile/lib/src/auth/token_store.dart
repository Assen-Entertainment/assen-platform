import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// The access + refresh token pair issued by the backend (`SignupOut`).
///
/// The ONLY session material the app persists (E6 auth, CONSTRAINTS #26). No
/// phone number, nickname, or any other PII is ever stored alongside it — the
/// tokens are opaque bearer/rotation strings, and the derived 인증 flags live on
/// the server (`GET /api/fan/me`), not here.
class AuthTokens {
  /// Creates a token pair.
  const AuthTokens({required this.accessToken, required this.refreshToken});

  /// The short-lived bearer token attached to authorized requests.
  final String accessToken;

  /// The long-lived token exchanged for a fresh pair via `POST /fan/refresh`.
  final String refreshToken;
}

/// Persists (or forgets) the fan's [AuthTokens] across app launches.
///
/// An interface so widget/unit tests can substitute an in-memory fake and
/// never touch a real platform channel (`flutter_secure_storage` has no test
/// binding).
abstract class TokenStore {
  /// Returns the stored token pair, or null when signed out / unreadable.
  Future<AuthTokens?> read();

  /// Persists [tokens], replacing any previous pair.
  Future<void> save(AuthTokens tokens);

  /// Forgets the stored pair (sign-out / refresh-family revocation).
  Future<void> clear();
}

/// Platform-secure [TokenStore] backed by [FlutterSecureStorage].
///
/// Stores the opaque token pair in the OS keystore (iOS Keychain / Android
/// Keystore / Windows DPAPI). Only the tokens are written — never PII — and the
/// values are never logged. The pair is persisted as a single JSON value under
/// one key so a write is atomic: an interrupted save can never leave an
/// old-refresh/new-access mix — a read sees either the complete new pair or the
/// prior complete pair, never a spliced one. Reads fail closed: a missing or
/// corrupt entry reads as signed out rather than throwing into the session
/// restore.
class SecureTokenStore implements TokenStore {
  /// Creates a store over [_storage].
  const SecureTokenStore(this._storage);

  final FlutterSecureStorage _storage;

  /// The single keystore key holding the JSON-encoded token pair. Namespaced to
  /// avoid colliding with any other secure entry the app may add later. One key
  /// (not two) is what makes writes atomic — see the class doc.
  static const String _pairKey = 'assen.auth.token_pair';

  /// JSON field for the access token within the stored pair.
  static const String _accessField = 'access_token';

  /// JSON field for the refresh token within the stored pair.
  static const String _refreshField = 'refresh_token';

  @override
  Future<AuthTokens?> read() async {
    final raw = await _storage.read(key: _pairKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) return null;
      final access = decoded[_accessField];
      final refresh = decoded[_refreshField];
      if (access is! String ||
          access.isEmpty ||
          refresh is! String ||
          refresh.isEmpty) {
        return null;
      }
      return AuthTokens(accessToken: access, refreshToken: refresh);
    } on FormatException {
      // A corrupt/garbled value: fail closed (signed out) rather than throw.
      return null;
    }
  }

  @override
  Future<void> save(AuthTokens tokens) async {
    final value = jsonEncode(<String, String>{
      _accessField: tokens.accessToken,
      _refreshField: tokens.refreshToken,
    });
    await _storage.write(key: _pairKey, value: value);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _pairKey);
  }
}

/// Provides the app's [TokenStore] (the platform-secure implementation).
///
/// Overridden with an in-memory fake in tests so the session flows can be
/// exercised without a platform channel.
final tokenStoreProvider = Provider<TokenStore>(
  (ref) => const SecureTokenStore(FlutterSecureStorage()),
);
