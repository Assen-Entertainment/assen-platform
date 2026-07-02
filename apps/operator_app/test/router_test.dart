import 'package:features/features.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/app.dart';
import 'package:operator_app/router/operator_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps [OperatorApp] with [repo] injected so the test and the app share one
/// session; settles the first frame.
Future<void> _pump(WidgetTester tester, MockAuthRepository repo) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const OperatorApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('operatorRoleAllows (P3a stub)', () {
    test('null session is rejected', () {
      expect(operatorRoleAllows(null), isFalse);
    });

    test('a present, non-expired session passes', () {
      final session = AuthSession(
        accessToken: 'tok',
        expiresAt: DateTime.now().add(const Duration(minutes: 5)),
      );
      expect(operatorRoleAllows(session), isTrue);
    });

    test('an expired session is rejected', () {
      final session = AuthSession(
        accessToken: 'tok',
        expiresAt: DateTime.now().subtract(const Duration(minutes: 1)),
      );
      expect(operatorRoleAllows(session), isFalse);
    });
  });

  group('operator router guard', () {
    testWidgets('unauthenticated cold start lands on /login', (tester) async {
      final repo = MockAuthRepository();
      addTearDown(repo.dispose);
      await _pump(tester, repo);

      expect(find.text('운영자 콘솔'), findsOneWidget);
      expect(find.byType(AssenOperatorDashboardTemplate), findsNothing);
    });

    testWidgets('after sign-in the dashboard (O1) is shown', (tester) async {
      final repo = MockAuthRepository();
      addTearDown(repo.dispose);
      await _pump(tester, repo);

      await repo.signIn(identifier: 'op@x', password: 'pw');
      await tester.pumpAndSettle();

      expect(find.byType(AssenOperatorDashboardTemplate), findsOneWidget);
    });

    testWidgets('expiring the session redirects back to /login', (
      tester,
    ) async {
      final repo = MockAuthRepository();
      addTearDown(repo.dispose);
      await _pump(tester, repo);
      await repo.signIn(identifier: 'op@x', password: 'pw');
      await tester.pumpAndSettle();
      expect(find.byType(AssenOperatorDashboardTemplate), findsOneWidget);

      repo.expireNow();
      await tester.pumpAndSettle();

      expect(find.text('운영자 콘솔'), findsOneWidget);
      expect(find.byType(AssenOperatorDashboardTemplate), findsNothing);
    });
  });
}
