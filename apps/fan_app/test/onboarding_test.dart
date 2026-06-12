import 'package:fan_app/screens/onboarding_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [OnboardingScreen] in a minimal router so its `context.go` CTAs have a
/// GoRouter ancestor (a login stub route receives the navigation).
Widget _host() {
  final router = GoRouter(
    initialLocation: '/onboarding',
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('LOGIN_STUB'))),
      ),
    ],
  );
  return MaterialApp.router(theme: AssenTheme.light(), routerConfig: router);
}

void main() {
  testWidgets('renders the first slide and the page dots', (tester) async {
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    expect(find.byType(PageView), findsOneWidget);
    expect(find.text('하츠코이를 손안에'), findsOneWidget);
    // First slide shows 다음 (not yet 시작하기) plus the skip + login affordances.
    expect(find.text('다음'), findsOneWidget);
    expect(find.text('건너뛰기'), findsOneWidget);
  });

  testWidgets('advancing through slides reaches the 시작하기 CTA', (tester) async {
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    // Tap 다음 twice to reach the last of three slides.
    await tester.tap(find.text('다음'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('다음'));
    await tester.pumpAndSettle();

    expect(find.text('체키로 남기는 추억'), findsOneWidget);
    expect(find.text('시작하기'), findsOneWidget);
  });

  testWidgets('건너뛰기 routes to /login', (tester) async {
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    await tester.tap(find.text('건너뛰기'));
    await tester.pumpAndSettle();

    expect(find.text('LOGIN_STUB'), findsOneWidget);
  });
}
