import 'package:fan_app/app.dart';
import 'package:fan_app/handoff.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
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

/// Resolves the live router so a test can drive URL-style navigation.
GoRouter _router(WidgetTester tester) =>
    GoRouter.of(tester.element(find.byType(Navigator).first));

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

    test('rejects backslash and control-char normalisation bypasses', () {
      // WHATWG URL parsing turns `\` into `/` and strips TAB/LF/CR, so these
      // would re-normalise into scheme-relative `//evil.example`.
      expect(LandingHandoff.safeReturnTo(r'/\evil.example'), FanRoutes.home);
      expect(LandingHandoff.safeReturnTo('/\t//evil.example'), FanRoutes.home);
      expect(LandingHandoff.safeReturnTo('/\n//evil.example'), FanRoutes.home);
      expect(LandingHandoff.safeReturnTo('/\r//evil.example'), FanRoutes.home);
    });

    test('keeps a rooted path with a colon in query or fragment', () {
      expect(
        LandingHandoff.safeReturnTo('/cast/mio?ref=a:b'),
        '/cast/mio?ref=a:b',
      );
      expect(LandingHandoff.safeReturnTo('/qr?t=12:30'), '/qr?t=12:30');
    });
  });

  group('fan router guard', () {
    testWidgets('non-web cold start lands on /onboarding', (tester) async {
      // ASS-141 적응형 셸: 기본 테스트 서피스(논리폭 800)는 M3 medium이므로 compact 뷰포트를 명시한다.
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await _pumpApp(tester);
      // kIsWeb is false under `flutter test`, so the first entry is the
      // onboarding screen (§4.3 모바일 첫 진입); web enters at /login.
      expect(find.text('이미 계정이 있어요'), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
    });

    testWidgets('unauthenticated protected route redirects to /login', (
      tester,
    ) async {
      // ASS-141 적응형 셸: 기본 테스트 서피스(논리폭 800)는 M3 medium이므로 compact 뷰포트를 명시한다.
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await _pumpApp(tester);
      _router(tester).go(FanRoutes.home);
      await tester.pumpAndSettle();

      // The login surface (brand + primary CTA) is shown, not a tab screen.
      expect(find.text('로그인'), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
    });

    testWidgets('after sign-in the shell shows /home with the 5-tab bar', (
      tester,
    ) async {
      // ASS-141 적응형 셸: 기본 테스트 서피스(논리폭 800)는 M3 medium이므로 compact 뷰포트를 명시한다.
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
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
      // ASS-141 적응형 셸: 기본 테스트 서피스(논리폭 800)는 M3 medium이므로 compact 뷰포트를 명시한다.
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
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
