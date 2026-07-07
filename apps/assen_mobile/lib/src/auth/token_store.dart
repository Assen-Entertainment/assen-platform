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
/// Stores the two opaque tokens in the OS keystore (iOS Keychain / Android
/// Keystore / Windows DPAPI). Only the tokens are written — never PII — and the
/// values are never logged. Reads fail closed: a missing/undecryptable entry
/// reads as signed out rather than throwing into the session restore.
class SecureTokenStore implements TokenStore {
  /// Creates a store over [_storage].
  const SecureTokenStore(this._storage);

  final FlutterSecureStorage _storage;

  /// Keystore key for the access token. Namespaced to avoid colliding with any
  /// other secure entry the app may add later.
  static const String _accessKey = 'assen.auth.access_token';

  /// Keystore key for the refresh token.
  static const String _refreshKey = 'assen.auth.refresh_token';

  @override
  Future<AuthTokens?> read() async {
    final access = await _storage.read(key: _accessKey);
    final refresh = await _storage.read(key: _refreshKey);
    if (access == null ||
        access.isEmpty ||
        refresh == null ||
        refresh.isEmpty) {
      return null;
    }
    return AuthTokens(accessToken: access, refreshToken: refresh);
  }

  @override
  Future<void> save(AuthTokens tokens) async {
    await _storage.write(key: _accessKey, value: tokens.accessToken);
    await _storage.write(key: _refreshKey, value: tokens.refreshToken);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}

/// Provides the app's [TokenStore] (the platform-secure implementation).
///
/// Overridden with an in-memory fake in tests so the session flows can be
/// exercised without a platform channel.
final tokenStoreProvider = Provider<TokenStore>(
  (ref) => const SecureTokenStore(FlutterSecureStorage()),
);
