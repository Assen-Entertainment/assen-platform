import 'package:features/src/auth/auth_session.dart';

/// The authentication boundary the rest of the app programs against.
///
/// Why an interface (not a concrete class): P3a wires a mock in-memory stub,
/// but the router guard, the providers and every routing test depend ONLY on
/// this contract. P3b replaces the implementation with the real opaque-token
/// client without touching a single caller or test (acceptance criterion;
/// CONSTRAINTS #31). The shape mirrors the standard opaque-token lifecycle
/// (ADR-0002): sign in, refresh, sign out, and observe the current session.
abstract interface class AuthRepository {
  /// The session right now, or null when signed out / expired.
  ///
  /// Synchronous so the router's `redirect` (which cannot await) can read it
  /// to decide between a protected route and /login.
  AuthSession? get currentSession;

  /// Emits whenever [currentSession] changes (sign in, refresh, expiry,
  /// sign out). The router bridges this to its `refreshListenable` so guards
  /// re-evaluate on every transition.
  Stream<AuthSession?> get sessionChanges;

  /// Exchanges credentials for a fresh [AuthSession].
  ///
  /// The mock accepts any non-empty [identifier]/[password] and mints a
  /// short-lived opaque token; the real implementation calls the auth endpoint.
  /// Implementations update [currentSession] and notify [sessionChanges].
  Future<AuthSession> signIn({
    required String identifier,
    required String password,
  });

  /// Renews the current session's token before it lapses.
  ///
  /// Returns the refreshed session. Throws [StateError] when there is no
  /// session to refresh (mirrors a 401 on the real refresh endpoint).
  Future<AuthSession> refresh();

  /// Clears the current session and notifies listeners (logout).
  Future<void> signOut();
}
