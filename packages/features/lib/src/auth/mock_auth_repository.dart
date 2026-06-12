import 'dart:async';

import 'package:features/src/auth/auth_repository.dart';
import 'package:features/src/auth/auth_session.dart';

/// An in-memory [AuthRepository] for P3a (no backend).
///
/// It honours the [AuthRepository] contract exactly so the real opaque-token
/// client can replace it in P3b with no caller or test changes (CONSTRAINTS
/// #31). Tokens are fabricated locally; nothing leaves the process. The
/// [sessionLifetime] is short so the rotation/expiry paths are exercisable, and
/// [expireNow] lets a test force the expired transition deterministically
/// (the real client cannot fake expiry, so this method is mock-only).
class MockAuthRepository implements AuthRepository {
  /// Creates the stub. [sessionLifetime] is how long a minted token stays
  /// valid (default 30 minutes — long enough to drive a session, short enough
  /// that callers must handle [refresh]).
  MockAuthRepository({
    this.sessionLifetime = const Duration(minutes: 30),
  });

  /// How long a freshly minted session stays valid.
  final Duration sessionLifetime;

  final StreamController<AuthSession?> _controller =
      StreamController<AuthSession?>.broadcast();

  AuthSession? _session;
  int _tokenSeq = 0;

  @override
  AuthSession? get currentSession => _session;

  @override
  Stream<AuthSession?> get sessionChanges => _controller.stream;

  @override
  Future<AuthSession> signIn({
    required String identifier,
    required String password,
  }) async {
    if (identifier.isEmpty || password.isEmpty) {
      // Mirrors a 400 from the real endpoint on empty credentials.
      throw ArgumentError('identifier and password must not be empty');
    }
    return _emit(_mintSession());
  }

  @override
  Future<AuthSession> refresh() async {
    if (_session == null) {
      // Mirrors a 401 on the real refresh endpoint when signed out.
      throw StateError('no session to refresh');
    }
    return _emit(_mintSession());
  }

  @override
  Future<void> signOut() async {
    _session = null;
    _controller.add(null);
  }

  /// Forces the current session to the expired state and notifies listeners.
  ///
  /// Mock-only: it back-dates the token so [AuthSession.isExpired] is true,
  /// letting the expired-session routing test drive the guard's /login redirect
  /// without waiting [sessionLifetime] in real time. No-op when signed out.
  void expireNow() {
    if (_session == null) return;
    _session = AuthSession(
      accessToken: _session!.accessToken,
      expiresAt: DateTime.now().subtract(const Duration(seconds: 1)),
    );
    _controller.add(_session);
  }

  /// Releases the broadcast controller. Call from a host's dispose.
  Future<void> dispose() => _controller.close();

  AuthSession _mintSession() {
    _tokenSeq += 1;
    // An opaque, locally-unique stand-in for the real bearer token. Callers
    // must not parse it (ADR-0002 opaque contract) — only its presence matters.
    final token = 'mock-${DateTime.now().microsecondsSinceEpoch}-$_tokenSeq';
    return AuthSession(
      accessToken: token,
      expiresAt: DateTime.now().add(sessionLifetime),
    );
  }

  AuthSession _emit(AuthSession session) {
    _session = session;
    _controller.add(session);
    return session;
  }
}
