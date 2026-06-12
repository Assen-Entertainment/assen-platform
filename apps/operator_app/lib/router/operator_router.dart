import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/router/routes.dart';
import 'package:operator_app/screens/operator_dashboard_screen.dart';
import 'package:operator_app/screens/operator_login_screen.dart';
import 'package:operator_app/screens/operator_placeholder_screen.dart';

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

/// Builds the operator-app [GoRouter] reading auth from [ref].
///
/// Guard contract (plan §4.3): an operator without a session (or one failing
/// the role gate) is redirected to /login; an authenticated, role-allowed
/// operator on /login is forwarded to /dashboard (O1). Expiry is a
/// session->null transition handled by the same unauth branch.
/// `refreshListenable` re-runs the guard on every session change.
///
/// The console is a flat set of routes (no tab shell): /dashboard is the hub
/// and /checkin·/cheki·/reports·/pos plus the /admin role slot are placeholder
/// pages reachable directly (deep link) until their tools land.
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
      GoRoute(
        path: OperatorRoutes.dashboard,
        builder: (context, state) => const OperatorDashboardScreen(),
      ),
      GoRoute(
        path: OperatorRoutes.checkin,
        builder: (context, state) => const OperatorPlaceholderScreen(
          title: '체크인 처리',
          message: '검색·수동 체크인 도구가 이곳에 들어옵니다.',
          icon: Icons.qr_code_scanner_outlined,
        ),
      ),
      GoRoute(
        path: OperatorRoutes.cheki,
        builder: (context, state) => const OperatorPlaceholderScreen(
          title: '체키 기록 입력',
          message: '캐스트·수량·POS 연결 입력이 이곳에 들어옵니다.',
          icon: Icons.photo_camera_outlined,
        ),
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
