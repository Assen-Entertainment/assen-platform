// Routing tests for the auth-guard redirect and the deep-linkable creator
// route. They drive the real GoRouter (shared through an UncontrolledProvider
// scope) with ProviderScope overrides — a fake discovery repo (no network) and,
// for the signed-in case, an authenticated AuthController override.

import 'package:assen_mobile/src/app/app.dart';
import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A discovery repository stand-in returning an empty feed without a network.
class _EmptyDiscoveryRepository implements DiscoveryRepository {
  @override
  Future<List<Creator>> fetchCreators() async => const [];
}

/// A creator repository stand-in returning a minimal profile without a network,
/// so the deep-link test can open the profile route without a real fetch.
class _FakeCreatorRepository implements CreatorRepository {
  @override
  Future<Creator> fetchCreator(String handle) async =>
      Creator(id: '1', handle: handle, displayName: handle);
}

/// An [AuthController] reporting a signed-in session, so the guard's
/// authenticated branch is exercisable without the (deferred) real login.
class _AuthedController extends AuthController {
  @override
  AuthState build() =>
      const AuthState(isAuthenticated: true, accessToken: 'test-token');
}

ProviderContainer _container({bool authenticated = false}) {
  return ProviderContainer(
    overrides: [
      discoveryRepositoryProvider.overrideWithValue(
        _EmptyDiscoveryRepository(),
      ),
      creatorRepositoryProvider.overrideWithValue(_FakeCreatorRepository()),
      if (authenticated)
        authControllerProvider.overrideWith(_AuthedController.new),
    ],
  );
}

/// Pumps [AssenApp] against [container] so tests can read the same
/// [routerProvider] instance to drive navigation.
Future<void> _pumpApp(WidgetTester tester, ProviderContainer container) async {
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const AssenApp()),
  );
  await tester.pump();
  await tester.pump();
}

void main() {
  testWidgets('a guest hitting /mypage is redirected to the login wall', (
    tester,
  ) async {
    final container = _container();
    addTearDown(container.dispose);
    await _pumpApp(tester, container);

    container.read(routerProvider).go(RoutePaths.mypage);
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인'), findsOneWidget); // login app-bar title
    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('an authenticated viewer is kept out of the login wall', (
    tester,
  ) async {
    final container = _container(authenticated: true);
    addTearDown(container.dispose);
    await _pumpApp(tester, container);

    container.read(routerProvider).go(RoutePaths.login);
    await tester.pump();
    await tester.pump();

    // Redirected back to discovery (home) — the login wall never renders.
    expect(find.text('로그인이 필요해요'), findsNothing);
    expect(find.text('둘러보기'), findsOneWidget); // discovery app-bar title
  });

  testWidgets('a /creator/:handle deep link opens the creator profile', (
    tester,
  ) async {
    final container = _container();
    addTearDown(container.dispose);
    await _pumpApp(tester, container);

    container.read(routerProvider).go(RoutePaths.creator('hoshino'));
    await tester.pump();
    await tester.pump();

    // The profile opened for the path handle: '@hoshino' appears in the app-bar
    // title and again in the header subtitle, so at least one is present.
    expect(find.text('@hoshino'), findsWidgets);
  });
}
