import 'dart:convert';

import 'package:features/src/auth/auth_session.dart';

/// Shared localStorage key for the ASS-140 landing-to-Flutter mock handoff.
const String assenSessionStorageKey = 'assen.session.v1';

/// Stores the current auth session synchronously for router boot guards.
///
/// The web shell must hydrate the mock session before the first GoRouter
/// redirect runs, so this contract intentionally avoids async APIs. The real
/// auth client can replace the repository later without changing callers.
abstract interface class SessionStore {
  /// Reads the last stored session, or null when none is available.
  AuthSession? read();

  /// Persists [session] for the next app boot.
  void write(AuthSession session);

  /// Removes any persisted session.
  void clear();
}

/// Process-local fallback store for mobile targets and tests.
///
/// It mirrors the web store contract without introducing platform storage into
/// tests or native builds.
class InMemorySessionStore implements SessionStore {
  AuthSession? _session;

  @override
  AuthSession? read() => _session;

  @override
  void write(AuthSession session) {
    _session = session;
  }

  @override
  void clear() {
    _session = null;
  }
}

/// Encodes a session into the landing/app localStorage contract.
///
/// Keys are deliberately fixed because `landing/src/main.js` writes the same
/// JSON object when it hands off to Flutter.
String encodeSession(AuthSession session) {
  return jsonEncode({
    'accessToken': session.accessToken,
    'expiresAt': session.expiresAt.toUtc().toIso8601String(),
  });
}

/// Decodes the landing/app session contract.
///
/// Invalid JSON, missing fields and wrong field types all return null so a
/// corrupted browser value never crashes the router during synchronous boot.
AuthSession? decodeSession(String raw) {
  try {
    final decoded = jsonDecode(raw);
    if (decoded is! Map) return null;
    final accessToken = decoded['accessToken'];
    final expiresAtRaw = decoded['expiresAt'];
    if (accessToken is! String || expiresAtRaw is! String) return null;
    final expiresAt = DateTime.tryParse(expiresAtRaw);
    if (expiresAt == null) return null;
    return AuthSession(
      accessToken: accessToken,
      expiresAt: expiresAt.toUtc(),
    );
  } on FormatException {
    return null;
  }
}
