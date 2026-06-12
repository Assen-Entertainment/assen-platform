import 'package:flutter/foundation.dart';

/// An authenticated session: an opaque access token plus its expiry.
///
/// Why opaque: P3a ships a mock auth stub, but the contract must match the real
/// opaque-token backend (ADR-0002) so the P3b integration swap is a drop-in —
/// callers (the router guard, repositories) only ever see a [String] token and
/// an [expiresAt] instant, never the token's internal shape. Treating the token
/// as opaque here is what lets the same routing tests re-run unchanged against
/// the real auth in P3b (acceptance criterion; CONSTRAINTS #31).
@immutable
class AuthSession {
  /// Creates a session for [accessToken] valid until [expiresAt].
  const AuthSession({required this.accessToken, required this.expiresAt});

  /// The opaque bearer token. Its internal structure is never inspected by
  /// callers — it is forwarded to the API client and compared for presence
  /// only (ADR-0002 opaque-token contract).
  final String accessToken;

  /// The instant the [accessToken] stops being valid. After this point the
  /// session is expired and the guard must redirect to /login.
  final DateTime expiresAt;

  /// Whether the session has expired relative to [now] (defaults to
  /// [DateTime.now]). Exposed so the guard and tests can probe expiry against a
  /// fixed clock without reaching into the token.
  bool isExpired({DateTime? now}) =>
      !(now ?? DateTime.now()).isBefore(expiresAt);

  @override
  bool operator ==(Object other) =>
      other is AuthSession &&
      other.accessToken == accessToken &&
      other.expiresAt == expiresAt;

  @override
  int get hashCode => Object.hash(accessToken, expiresAt);
}
