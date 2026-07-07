import 'package:assen_mobile/src/app/app_shell.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/creator/creator_screen.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:assen_mobile/src/feed/feed_screen.dart';
import 'package:assen_mobile/src/login/login_screen.dart';
import 'package:assen_mobile/src/mypage/mypage_screen.dart';
import 'package:assen_mobile/src/notifications/notifications_screen.dart';
import 'package:assen_mobile/src/post/post_screen.dart';
import 'package:assen_mobile/src/search/search_screen.dart';
import 'package:assen_mobile/src/store/product_screen.dart';
import 'package:assen_mobile/src/store/store_screen.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Canonical route locations.
///
/// Centralised so tab switches, deep links, and redirects never hard-code path
/// strings that could drift apart.
abstract final class RoutePaths {
  /// The home tab — creator discovery (the default location).
  static const String discovery = '/discovery';

  /// The search tab.
  static const String search = '/search';

  /// The notifications tab.
  static const String notifications = '/notifications';

  /// The 마이 (my page) tab — auth-gated.
  static const String mypage = '/mypage';

  /// The login wall shown to guests hitting a protected route.
  static const String login = '/login';

  /// The global feed of recent posts (reached from the discovery shortcut).
  static const String feed = '/feed';

  /// The global store / product catalog (reached from the discovery shortcut).
  static const String store = '/store';

  /// Builds the deep-linkable creator profile location for [handle].
  static String creator(String handle) => '/creator/$handle';

  /// Builds the post detail location for [id].
  static String post(String id) => '/post/$id';

  /// Builds the product detail location for [id].
  static String product(String id) => '/product/$id';
}

// Root navigator key so pushed routes (creator, login) sit above the shell.
final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();

/// The application [GoRouter].
///
/// Wires the four-branch [StatefulShellRoute] (bottom-nav shell), the
/// deep-linkable `/creator/:handle` route, and the login wall, plus the
/// auth-guard `redirect`. Auth changes are bridged to go_router's
/// `refreshListenable` through a [ValueNotifier] (fed by `ref.listen`) so the
/// redirect re-runs on sign-in/out without a `ChangeNotifierProvider`.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref
    ..listen(authControllerProvider, (_, _) => refresh.value++)
    ..onDispose(refresh.dispose);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: RoutePaths.discovery,
    refreshListenable: refresh,
    redirect: (context, state) {
      final isAuthenticated = ref.read(authControllerProvider).isAuthenticated;
      final location = state.matchedLocation;
      // The 마이 tab is the only auth-gated destination for now; guests are
      // routed to the login wall (social login is an E6 gate).
      if (location.startsWith(RoutePaths.mypage) && !isAuthenticated) {
        return RoutePaths.login;
      }
      // Keep signed-in viewers out of the login wall.
      if (location == RoutePaths.login && isAuthenticated) {
        return RoutePaths.discovery;
      }
      return null;
    },
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: RoutePaths.discovery,
                builder: (context, state) => const DiscoveryScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: RoutePaths.search,
                builder: (context, state) => const SearchScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: RoutePaths.notifications,
                builder: (context, state) => const NotificationsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: RoutePaths.mypage,
                builder: (context, state) => const MyPageScreen(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/creator/:handle',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            CreatorScreen(handle: state.pathParameters['handle']!),
      ),
      GoRoute(
        path: RoutePaths.feed,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const FeedScreen(),
      ),
      GoRoute(
        path: '/post/:id',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            PostScreen(postId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: RoutePaths.store,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const StoreScreen(),
      ),
      GoRoute(
        path: '/product/:id',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            ProductScreen(productId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: RoutePaths.login,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const LoginScreen(),
      ),
    ],
  );
});
