import 'package:fan_app/handoff.dart';
import 'package:fan_app/router/routes.dart';
import 'package:fan_app/screens/cast_profile_screen.dart';
import 'package:fan_app/screens/checkin_complete_screen.dart';
import 'package:fan_app/screens/cheki_screen.dart';
import 'package:fan_app/screens/event_screen.dart';
import 'package:fan_app/screens/home_screen.dart';
import 'package:fan_app/screens/login_screen.dart';
import 'package:fan_app/screens/my_screen.dart';
import 'package:fan_app/screens/notification_settings_screen.dart';
import 'package:fan_app/screens/onboarding_screen.dart';
import 'package:fan_app/screens/points_history_screen.dart';
import 'package:fan_app/screens/qr_screen.dart';
import 'package:fan_app/screens/reservation_screen.dart';
import 'package:fan_app/screens/schedule_screen.dart';
import 'package:fan_app/screens/signup_screen.dart';
import 'package:fan_app/screens/visit_history_screen.dart';
import 'package:fan_app/shell/fan_shell.dart';
import 'package:features/features.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Routes that are reachable without a session (the auth surfaces).
///
/// `/onboarding` is included so first-run mobile users are not bounced to
/// /login before they have seen it. Everything else requires auth.
const Set<String> _publicLocations = {
  FanRoutes.onboarding,
  FanRoutes.login,
  FanRoutes.signup,
};

/// Builds the fan-app [GoRouter] reading auth from [ref].
///
/// Guard contract (plan §4.3): an unauthenticated user on a protected route is
/// redirected to /login carrying `return_to` (so a deep link such as /qr or
/// /cast/:id resumes after sign-in); an authenticated user on /login or /signup
/// is forwarded to /home. Expiry is a session->null transition, so the same
/// unauth branch handles it. `refreshListenable` re-runs the guard on every
/// session change ([authListenableProvider]).
///
/// The 5-tab post-auth area is a [StatefulShellRoute.indexedStack] so each tab
/// keeps its own `Navigator` and state (5탭 상태 보존) and browser back pops the
/// active branch before switching tabs — the conventional go_router shell idiom
/// (CONSTRAINTS #40, no exotic structure).
GoRouter buildFanRouter(Ref ref) {
  return GoRouter(
    // §4.3: the Flutter web entry is /login (the landing handles `/`); the
    // mobile first entry is the onboarding screen. A seen-once flag (skip
    // onboarding on later launches) needs persistence and lands post-P3a.
    initialLocation: kIsWeb ? FanRoutes.login : FanRoutes.onboarding,
    refreshListenable: ref.watch(authListenableProvider),
    redirect: (context, state) {
      // Read the session from the repository (the source of truth), which is
      // always synchronously current. The Notifier's state is eventually
      // consistent via a stream, so it can lag the refreshListenable's own
      // bump; the repository never does.
      final session = ref.read(authRepositoryProvider).currentSession;
      // A present but expired session counts as signed out, so an expiry
      // transition redirects to /login (acceptance: expired session).
      final signedIn = session != null && !session.isExpired();
      final location = state.matchedLocation;
      final isPublic = _publicLocations.contains(location);

      if (!signedIn && !isPublic) {
        // Preserve the attempted location so sign-in can resume it.
        final returnTo = state.uri.toString();
        return Uri(
          path: FanRoutes.login,
          queryParameters: {LandingHandoff.returnToParam: returnTo},
        ).toString();
      }

      // A signed-in user has no business on any pre-auth surface (login,
      // signup, onboarding) — bounce to /home so e.g. sign-in from the
      // onboarding CTA lands in the shell.
      if (signedIn && isPublic) {
        return FanRoutes.home;
      }

      return null;
    },
    routes: [
      GoRoute(
        path: FanRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: FanRoutes.login,
        builder: (context, state) {
          final raw = state.uri.queryParameters[LandingHandoff.returnToParam];
          return LoginScreen(returnTo: LandingHandoff.safeReturnTo(raw));
        },
      ),
      GoRoute(
        path: FanRoutes.signup,
        builder: (context, state) => const SignupScreen(),
      ),
      GoRoute(
        path: FanRoutes.qr,
        builder: (context, state) => const QrScreen(),
      ),
      GoRoute(
        path: FanRoutes.checkinComplete,
        builder: (context, state) => const CheckinCompleteScreen(),
      ),
      GoRoute(
        path: '/cast/:id',
        name: FanRoutes.castName,
        builder: (context, state) =>
            CastProfileScreen(castId: state.pathParameters['id'] ?? 'mio'),
      ),
      GoRoute(
        path: FanRoutes.events,
        builder: (context, state) => const EventListScreen(),
        routes: [
          GoRoute(
            path: ':id',
            name: FanRoutes.eventName,
            builder: (context, state) => EventDetailScreen(
              eventId: state.pathParameters['id'] ?? 'mio-birthday-week',
            ),
          ),
        ],
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            FanShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: FanRoutes.home,
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: FanRoutes.schedule,
                builder: (context, state) => const ScheduleScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: FanRoutes.reservation,
                builder: (context, state) => const ReservationScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: FanRoutes.cheki,
                builder: (context, state) => const ChekiScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: FanRoutes.my,
                builder: (context, state) => const MyScreen(),
                routes: [
                  GoRoute(
                    path: 'visits',
                    builder: (context, state) => const VisitHistoryScreen(),
                  ),
                  GoRoute(
                    path: 'points',
                    builder: (context, state) => const PointsHistoryScreen(),
                  ),
                  GoRoute(
                    path: 'notifications',
                    builder: (context, state) =>
                        const NotificationSettingsScreen(),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
  );
}

/// The fan-app router provider.
///
/// A [Provider] so the router lives for the app's lifetime and can read auth
/// state. Consumed once by the root `MaterialApp.router`.
final Provider<GoRouter> fanRouterProvider = Provider<GoRouter>(buildFanRouter);
