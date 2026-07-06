import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Immutable authentication state for the session.
///
/// Holds whether a viewer is signed in and, if so, the opaque access token used
/// to authorize API calls. Real credentials are not persisted yet — secure
/// token storage and social login are E6 gates (see [AuthController]).
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
  /// out. The refresh-rotation counterpart lives in the API auth interceptor.
  final String? accessToken;
}

/// Owns the session [AuthState].
///
/// Scaffold only: the app ships signed-out so the auth-guard redirect and the
/// login wall are exercisable; the real sign-in path is deferred (see below).
class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() {
    // TODO(assen): wire social login + secure-storage token persistence and
    // refresh rotation (E6 gate); until then signOut is the only transition.
    return const AuthState.unauthenticated();
  }

  /// Clears the session, returning to the signed-out state.
  void signOut() => state = const AuthState.unauthenticated();
}

/// Exposes the session [AuthState] and its [AuthController].
final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
