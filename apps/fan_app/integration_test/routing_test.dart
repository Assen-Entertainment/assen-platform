// Routing integration tests (acceptance — plan §4.3 / ASS-131).
//
// The four scenarios required by the spec, each driving the real [FanApp] over
// the in-memory mock auth (swapped in via authRepositoryProvider so the test
// and the app share one session):
//   1. Browser back — pop a sub-route and switch tabs inside the shell.
//   2. Deep link — cold-start directly into /qr and /cast/:id.
//   3. QR entry — unauthenticated /qr redirects to /login, then resumes /qr.
//   4. Expired session — a session->expired transition redirects to /login.
//
// They are written against the AuthRepository contract only, so P3b can re-run
// them unchanged against the real opaque-token client (CONSTRAINTS #31).
import 'package:fan_app/app.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps [FanApp] with [repo] injected, settling the first frame.
Future<void> _pump(WidgetTester tester, MockAuthRepository repo) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const FanApp(),
    ),
  );
  await tester.pumpAndSettle();
}

/// Signs in through [repo] (the app observes the same session) and settles.
Future<void> _signIn(WidgetTester tester, MockAuthRepository repo) async {
  await repo.signIn(identifier: 'fan@assen.example', password: 'mock');
  await tester.pumpAndSettle();
}

/// Sends a system back-button event (the mobile/browser back analogue).
Future<void> _systemBack(WidgetTester tester) async {
  await tester.binding.handlePopRoute();
  await tester.pumpAndSettle();
}

/// Navigates the running app to [location] (an in-app deep link), as if the URL
/// bar changed, then settles. Resolves the live GoRouter from the tree.
Future<void> _go(WidgetTester tester, String location) async {
  GoRouter.of(tester.element(find.byType(Navigator).first)).go(location);
  await tester.pumpAndSettle();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('1. browser back: pop a sub-route and switch tabs in the shell', (
    tester,
  ) async {
    final repo = MockAuthRepository();
    addTearDown(repo.dispose);
    await _pump(tester, repo);
    await _signIn(tester, repo);

    // On 마이, push the QR sub-route, then system-back pops it (not the app).
    await tester.tap(find.text('마이').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('회원증 QR'));
    await tester.pumpAndSettle();
    expect(find.byType(AssenQrDisplay), findsOneWidget);

    await _systemBack(tester);
    expect(find.byType(AssenQrDisplay), findsNothing);
    expect(find.text('로그아웃'), findsOneWidget); // back on the 마이 tab

    // Switch tabs, then confirm the tab bar drives the branch.
    await tester.tap(find.text('출근표').last);
    await tester.pumpAndSettle();
    expect(find.text('출근 캐스트'), findsOneWidget);

    await tester.tap(find.text('홈').last);
    await tester.pumpAndSettle();
    expect(find.byType(AssenMembershipCard), findsOneWidget);
  });

  testWidgets('2. deep link: cold start into /qr and /cast/:id', (
    tester,
  ) async {
    // /qr cold start (authenticated) renders the QR directly.
    final repo = MockAuthRepository();
    addTearDown(repo.dispose);
    await repo.signIn(identifier: 'fan@assen.example', password: 'mock');
    await _pump(tester, repo);
    // Drive the deep link after boot (cold-start location for the running app).
    await _go(tester, FanRoutes.qr);
    expect(find.byType(AssenQrDisplay), findsOneWidget);

    // /cast/:id cold start renders that cast's profile.
    await _go(tester, FanRoutes.castPath('yuki'));
    expect(find.byType(AssenCastProfileTemplate), findsOneWidget);
    expect(find.text('유키'), findsWidgets);
  });

  testWidgets('3. QR entry: unauth /qr -> /login -> resume /qr after sign-in', (
    tester,
  ) async {
    final repo = MockAuthRepository();
    addTearDown(repo.dispose);
    await _pump(tester, repo); // unauthenticated

    // Attempt the QR deep link while signed out -> guard redirects to /login.
    await _go(tester, FanRoutes.qr);
    expect(find.text('로그인'), findsOneWidget);
    expect(find.byType(AssenQrDisplay), findsNothing);

    // The login screen carried return_to=/qr; signing in there resumes /qr.
    // (LoginScreen reads return_to from the redirected location and navigates
    // to it on success — drive its primary CTA.)
    await tester.tap(find.widgetWithText(AssenButton, '로그인'));
    await tester.pumpAndSettle();
    expect(find.byType(AssenQrDisplay), findsOneWidget);
  });

  testWidgets('4. expired session: expiry transition redirects to /login', (
    tester,
  ) async {
    final repo = MockAuthRepository();
    addTearDown(repo.dispose);
    await _pump(tester, repo);
    await _signIn(tester, repo);
    expect(find.byType(AssenTabBar), findsOneWidget); // in the shell

    // Force the session to expire -> the guard redirects to /login.
    repo.expireNow();
    await tester.pumpAndSettle();

    expect(find.text('로그인'), findsOneWidget);
    expect(find.byType(AssenTabBar), findsNothing);
  });
}
