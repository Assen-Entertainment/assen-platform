import 'package:fan_app/app.dart';
import 'package:fan_app/handoff.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps [FanApp] under a [ProviderScope]; returns the shared mock repo so a
/// test can sign in / expire deterministically. The repo is created once and
/// injected so the test and the app observe the same session.
Future<MockAuthRepository> _pumpApp(WidgetTester tester) async {
  final repo = MockAuthRepository();
  addTearDown(repo.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const FanApp(),
    ),
  );
  await tester.pumpAndSettle();
  return repo;
}

void main() {
  group('LandingHandoff.safeReturnTo', () {
    test('keeps a root-relative in-app path', () {
      expect(LandingHandoff.safeReturnTo('/qr'), '/qr');
      expect(LandingHandoff.safeReturnTo('/cast/mio'), '/cast/mio');
    });

    test('falls back to /home for empty or null', () {
      expect(LandingHandoff.safeReturnTo(null), FanRoutes.home);
      expect(LandingHandoff.safeReturnTo(''), FanRoutes.home);
    });

    test(
      'rejects open-redirect shapes (scheme-relative, absolute, scheme)',
      () {
        expect(LandingHandoff.safeReturnTo('//evil.example'), FanRoutes.home);
        expect(
          LandingHandoff.safeReturnTo('https://evil.example'),
          FanRoutes.home,
        );
        expect(
          LandingHandoff.safeReturnTo('javascript:alert(1)'),
          FanRoutes.home,
        );
        expect(LandingHandoff.safeReturnTo('relative/path'), FanRoutes.home);
      },
    );
  });

  group('fan router guard', () {
    testWidgets('unauthenticated cold start lands on /login', (tester) async {
      await _pumpApp(tester);
      // The login surface (brand + primary CTA) is shown, not a tab screen.
      expect(find.text('로그인'), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
    });

    testWidgets('after sign-in the shell shows /home with the 5-tab bar', (
      tester,
    ) async {
      final repo = await _pumpApp(tester);
      await repo.signIn(identifier: 'fan@x', password: 'pw');
      await tester.pumpAndSettle();

      expect(find.byType(AssenTabBar), findsOneWidget);
      // Home hero (membership card) proves we are on the home branch.
      expect(find.byType(AssenMembershipCard), findsOneWidget);
    });

    testWidgets('signing out from an authed session redirects to /login', (
      tester,
    ) async {
      final repo = await _pumpApp(tester);
      await repo.signIn(identifier: 'fan@x', password: 'pw');
      await tester.pumpAndSettle();
      expect(find.byType(AssenTabBar), findsOneWidget);

      await repo.signOut();
      await tester.pumpAndSettle();

      expect(find.text('로그인'), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
    });
  });

  group('5-tab shell switching', () {
    testWidgets('tapping each tab swaps the branch screen', (tester) async {
      final repo = await _pumpApp(tester);
      await repo.signIn(identifier: 'fan@x', password: 'pw');
      await tester.pumpAndSettle();

      // Home -> 출근표 tab.
      await tester.tap(find.text('출근표').last);
      await tester.pumpAndSettle();
      expect(find.text('출근 캐스트'), findsOneWidget);

      // -> 예약 tab (placeholder empty-state CTA).
      await tester.tap(find.text('예약').last);
      await tester.pumpAndSettle();
      expect(find.text('아직 예약이 없어요'), findsOneWidget);

      // -> 마이 tab (hub with 로그아웃 row).
      await tester.tap(find.text('마이').last);
      await tester.pumpAndSettle();
      expect(find.text('로그아웃'), findsOneWidget);
    });
  });
}
