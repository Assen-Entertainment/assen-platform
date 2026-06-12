import 'package:features/src/auth/auth_repository.dart';
import 'package:features/src/auth/auth_session.dart';
import 'package:features/src/auth/mock_auth_repository.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The app-wide [AuthRepository].
///
/// Defaults to the [MockAuthRepository] (P3a, no backend). P3b overrides this
/// provider with the real opaque-token client — the only swap point — and every
/// consumer (guard, screens, tests) keeps working unchanged (CONSTRAINTS #31).
/// Declared with the Riverpod 3.x top-level [Provider] API; 2.x syntax is
/// forbidden (CONSTRAINTS #40).
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final repo = MockAuthRepository();
  ref.onDispose(repo.dispose);
  return repo;
});

/// The current [AuthSession] (null when signed out / expired).
///
/// A Riverpod 3.x [Notifier] seeded from the repository and updated through it,
/// so UI and the router observe one source of truth. The router does not watch
/// this directly (its `redirect` is synchronous); it bridges
/// [authListenableProvider] instead.
final authSessionProvider = NotifierProvider<AuthSessionNotifier, AuthSession?>(
  AuthSessionNotifier.new,
);

/// Holds and mutates the active [AuthSession] via the [AuthRepository].
///
/// All mutations delegate to the repository so the mock today and the real
/// client in P3b share identical call sites.
class AuthSessionNotifier extends Notifier<AuthSession?> {
  @override
  AuthSession? build() {
    final repo = ref.watch(authRepositoryProvider);
    final sub = repo.sessionChanges.listen((session) => state = session);
    ref.onDispose(sub.cancel);
    return repo.currentSession;
  }

  /// Signs in with [identifier]/[password] and stores the session.
  Future<void> signIn({
    required String identifier,
    required String password,
  }) async {
    final repo = ref.read(authRepositoryProvider);
    state = await repo.signIn(identifier: identifier, password: password);
  }

  /// Clears the session (logout).
  Future<void> signOut() async {
    await ref.read(authRepositoryProvider).signOut();
    state = null;
  }
}

/// A [Listenable] view of the auth session for `GoRouter.refreshListenable`.
///
/// `redirect` cannot await a stream, so the router needs a synchronous signal
/// that *something* changed; this adapter fires `notifyListeners` on every
/// session transition (sign in, refresh, expiry, sign out), prompting the
/// router to re-run its guard. Kept separate from the [Notifier] because the
/// router lives outside the widget tree and consumes a plain [Listenable].
final authListenableProvider = Provider<Listenable>((ref) {
  final notifier = _AuthListenable();
  final sub = ref
      .watch(authRepositoryProvider)
      .sessionChanges
      .listen((_) => notifier.bump());
  ref.onDispose(() {
    sub.cancel();
    notifier.dispose();
  });
  return notifier;
});

/// A trivial [ChangeNotifier] that exposes a public [bump] to re-notify.
class _AuthListenable extends ChangeNotifier {
  void bump() => notifyListeners();
}
