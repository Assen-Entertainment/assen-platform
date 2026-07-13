import 'package:assen_mobile/src/app/app_shell.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/checkout/checkout_screen.dart';
import 'package:assen_mobile/src/creator/creator_screen.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:assen_mobile/src/feed/feed_screen.dart';
import 'package:assen_mobile/src/followers/followers_screen.dart';
import 'package:assen_mobile/src/login/login_screen.dart';
import 'package:assen_mobile/src/membership/subscriptions_screen.dart';
import 'package:assen_mobile/src/mypage/mypage_screen.dart';
import 'package:assen_mobile/src/notifications/notifications_screen.dart';
import 'package:assen_mobile/src/onboarding/onboarding_screen.dart';
import 'package:assen_mobile/src/orders/order_detail_screen.dart';
import 'package:assen_mobile/src/orders/orders_screen.dart';
import 'package:assen_mobile/src/post/post_screen.dart';
import 'package:assen_mobile/src/search/search_screen.dart';
import 'package:assen_mobile/src/settings/account_screen.dart';
import 'package:assen_mobile/src/settings/blocked_screen.dart';
import 'package:assen_mobile/src/settings/notification_settings_screen.dart';
import 'package:assen_mobile/src/settings/payment_methods_screen.dart';
import 'package:assen_mobile/src/settings/settings_screen.dart';
import 'package:assen_mobile/src/store/product_screen.dart';
import 'package:assen_mobile/src/store/store_screen.dart';
import 'package:assen_mobile/src/studio/studio_posts_screen.dart';
import 'package:assen_mobile/src/studio/studio_products_screen.dart';
import 'package:assen_mobile/src/studio/studio_screen.dart';
import 'package:assen_mobile/src/studio/studio_tiers_screen.dart';
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

  /// The signed-in fan's own orders (reached from the 마이 tab).
  static const String orders = '/orders';

  /// Builds the order-detail location for [id] (reached from the orders list).
  static String orderDetail(String id) => '/orders/$id';

  /// The 내 구독 (subscriptions) screen (reached from the 마이 tab).
  static const String subscriptions = '/mypage/subscriptions';

  /// The creator owner's studio dashboard (reached from the 마이 tab).
  static const String studio = '/studio';

  /// The 게시물 관리 screen — the creator's own posts (reached from 스튜디오).
  static const String studioPosts = '/studio/posts';

  /// The 상품 관리 screen — the creator's catalog (reached from 스튜디오).
  static const String studioProducts = '/studio/products';

  /// The 멤버십 관리 screen — the creator's tiers (reached from 스튜디오).
  static const String studioMembership = '/studio/membership';

  /// The account settings screen (reached from the 마이 tab).
  static const String settings = '/settings';

  /// The 계정 관리 screen — profile info + 회원 탈퇴 (reached from 설정).
  static const String settingsAccount = '/settings/account';

  /// The 알림 설정 screen — per-channel marketing consent (reached from 설정).
  static const String settingsNotifications = '/settings/notifications';

  /// The 차단 관리 screen — the fan's personal block list (reached from 설정).
  static const String settingsBlocked = '/settings/blocked';

  /// The 결제 수단 screen — the fan's saved payment methods (reached from 설정).
  static const String settingsPayments = '/settings/payments';

  /// The app intro / onboarding (reached from 설정 → "앱 소개 다시 보기").
  static const String onboarding = '/onboarding';

  /// Builds the deep-linkable creator profile location for [handle].
  static String creator(String handle) => '/creator/$handle';

  /// Builds the followers-list location for the creator [handle].
  static String followers(String handle) => '/creator/$handle/followers';

  /// Builds the post detail location for [id].
  static String post(String id) => '/post/$id';

  /// Builds the product detail location for [id].
  static String product(String id) => '/product/$id';

  /// Builds the (mock) checkout location for [productId], with optional [qty]
  /// and [option] carried as query parameters.
  static String checkout(
    String productId, {
    int qty = 1,
    String option = '',
  }) {
    final params = <String, String>{
      if (qty != 1) 'qty': '$qty',
      if (option.isNotEmpty) 'opt': option,
    };
    if (params.isEmpty) return '/checkout/$productId';
    return '/checkout/$productId?${Uri(queryParameters: params).query}';
  }
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
        path: '/creator/:handle/followers',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            FollowersScreen(handle: state.pathParameters['handle']!),
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
        path: '/checkout/:productId',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final rawQty = int.tryParse(state.uri.queryParameters['qty'] ?? '');
          return CheckoutScreen(
            productId: state.pathParameters['productId']!,
            qty: rawQty == null || rawQty < 1 ? 1 : rawQty,
            option: state.uri.queryParameters['opt'] ?? '',
          );
        },
      ),
      GoRoute(
        path: RoutePaths.orders,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const OrdersScreen(),
      ),
      GoRoute(
        path: '/orders/:id',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) =>
            OrderDetailScreen(orderId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: RoutePaths.subscriptions,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SubscriptionsScreen(),
      ),
      GoRoute(
        path: RoutePaths.studio,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const StudioScreen(),
      ),
      GoRoute(
        path: RoutePaths.studioPosts,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const StudioPostsScreen(),
      ),
      GoRoute(
        path: RoutePaths.studioProducts,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const StudioProductsScreen(),
      ),
      GoRoute(
        path: RoutePaths.studioMembership,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const StudioTiersScreen(),
      ),
      GoRoute(
        path: RoutePaths.settings,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: RoutePaths.settingsAccount,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const AccountScreen(),
      ),
      GoRoute(
        path: RoutePaths.settingsNotifications,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const NotificationSettingsScreen(),
      ),
      GoRoute(
        path: RoutePaths.settingsBlocked,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const BlockedScreen(),
      ),
      GoRoute(
        path: RoutePaths.settingsPayments,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const PaymentMethodsScreen(),
      ),
      GoRoute(
        path: RoutePaths.onboarding,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: RoutePaths.login,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const LoginScreen(),
      ),
    ],
  );
});
