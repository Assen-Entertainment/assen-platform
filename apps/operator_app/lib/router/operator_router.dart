import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/router/routes.dart';
import 'package:operator_app/screens/operator_checkin_screen.dart';
import 'package:operator_app/screens/operator_cheki_screen.dart';
import 'package:operator_app/screens/operator_dashboard_screen.dart';
import 'package:operator_app/screens/operator_login_screen.dart';
import 'package:operator_app/screens/operator_placeholder_screen.dart';
import 'package:operator_app/shell/operator_shell.dart';

/// Whether [session] satisfies the operator role gate.
///
/// P3a STUB: any present, non-expired session passes (role判定 lands in P3b). It
/// is a named seam so P3b swaps the body to inspect the real token's claims
/// without touching the router wiring or the routing tests (CONSTRAINTS #31).
/// An expired session fails the gate, so expiry redirects to /login.
///
/// SECURITY (P3b 필수): the auth providers are shared with fan_app, so until
/// real role-claim validation lands here, a session issued for a *fan* would
/// pass this gate — a privilege-escalation surface. Acceptable in P3a only
/// because the apps ship as separate binaries against a mock repo; P3b MUST
/// replace this body before any real token reaches the operator console.
bool operatorRoleAllows(AuthSession? session) =>
    session != null && !session.isExpired();

/// Console shell branch locations, ordered to match
/// [OperatorShell.destinations].
///
/// The index order is the contract the shell relies on: a tapped rail/tab
/// destination at index `i` navigates to `shellLocations[i]`, and the active
/// location maps back to the selected index. `/login` and `/admin` are absent
/// because they live outside the shell. Exposed for tests that pin this
/// index↔location round-trip (the highest-value invariant of the shell).
@visibleForTesting
const List<String> shellLocations = <String>[
  OperatorRoutes.dashboard,
  OperatorRoutes.checkin,
  OperatorRoutes.cheki,
  OperatorRoutes.reports,
  OperatorRoutes.pos,
];

/// The console destination index for [location] (0 when it is not a shell
/// route).
///
/// Exact-equality is tried before the prefix arm so sibling routes whose paths
/// share a prefix do not collide — notably `/checkin` resolves to its own index
/// rather than matching `/cheki`.
@visibleForTesting
int shellIndexForLocation(String location) {
  final index = shellLocations.indexWhere(
    (path) => location == path || location.startsWith('$path/'),
  );
  return index < 0 ? 0 : index;
}

/// Builds the operator-app [GoRouter] reading auth from [ref].
///
/// Guard contract (plan §4.3): an operator without a session (or one failing
/// the role gate) is redirected to /login; an authenticated, role-allowed
/// operator on /login is forwarded to /dashboard (O1). Expiry is a
/// session->null transition handled by the same unauth branch.
/// `refreshListenable` re-runs the guard on every session change.
///
/// The post-auth destinations (/dashboard·/checkin·/cheki·/reports·/pos) share
/// one adaptive [OperatorShell] (navigation rail on web/tablet, bottom bar on
/// mobile) via a plain [ShellRoute] — not a stateful one, so only the active
/// child builds. /login and the /admin role slot stay outside the shell, so the
/// guard and the deep-link-only admin route are unaffected.
GoRouter buildOperatorRouter(Ref ref) {
  return GoRouter(
    initialLocation: OperatorRoutes.login,
    refreshListenable: ref.watch(authListenableProvider),
    redirect: (context, state) {
      // The repository is the synchronously-current source of truth; the
      // Notifier's state lags via a stream (see fan_router for the rationale).
      final session = ref.read(authRepositoryProvider).currentSession;
      final allowed = operatorRoleAllows(session);
      final atLogin = state.matchedLocation == OperatorRoutes.login;

      if (!allowed && !atLogin) return OperatorRoutes.login;
      if (allowed && atLogin) return OperatorRoutes.dashboard;
      return null;
    },
    routes: [
      GoRoute(
        path: OperatorRoutes.login,
        builder: (context, state) => const OperatorLoginScreen(),
      ),
      // The post-auth console destinations share one adaptive shell (rail on
      // web/tablet, bottom bar on mobile). A plain ShellRoute (not a stateful
      // one) builds only the active child, so the guard tests still see exactly
      // one destination screen at a time.
      ShellRoute(
        builder: (context, state, child) => OperatorShell(
          currentIndex: shellIndexForLocation(state.matchedLocation),
          onDestinationSelected: (index) => context.go(shellLocations[index]),
          child: child,
        ),
        routes: [
          GoRoute(
            path: OperatorRoutes.dashboard,
            builder: (context, state) => const OperatorDashboardScreen(),
          ),
          GoRoute(
            path: OperatorRoutes.checkin,
            builder: (context, state) => const OperatorCheckinScreen(),
          ),
          GoRoute(
            path: OperatorRoutes.cheki,
            builder: (context, state) => const OperatorChekiScreen(),
          ),
          GoRoute(
            path: OperatorRoutes.reports,
            builder: (context, state) => const OperatorPlaceholderScreen(
              title: '리포트',
              message: '일일 집계와 마감 리포트가 이곳에 들어옵니다.',
              icon: Icons.assessment_outlined,
            ),
          ),
          GoRoute(
            path: OperatorRoutes.pos,
            builder: (context, state) => const OperatorPlaceholderScreen(
              title: 'POS 마감 대조',
              message: 'POS 마감 대조 도구가 이곳에 들어옵니다.',
              icon: Icons.point_of_sale_outlined,
            ),
          ),
        ],
      ),
      // Admin stays outside the shell: a higher-role, deep-link-only slot that
      // is not a primary console destination (no rail/tab entry).
      GoRoute(
        path: OperatorRoutes.admin,
        builder: (context, state) => const OperatorPlaceholderScreen(
          title: '관리자',
          message: '권한 관리 등 상위 롤 전용 기능이 이곳에 들어옵니다.',
          icon: Icons.admin_panel_settings_outlined,
        ),
      ),
    ],
  );
}

/// The operator-app router provider (lives for the app's lifetime).
final Provider<GoRouter> operatorRouterProvider = Provider<GoRouter>(
  buildOperatorRouter,
);
