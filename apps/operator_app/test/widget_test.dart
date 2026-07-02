import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/main.dart';

void main() {
  testWidgets('OperatorApp boots into the login entry point (P3a router)', (
    tester,
  ) async {
    // OperatorApp is a ConsumerWidget driving MaterialApp.router; it needs a
    // ProviderScope ancestor. The guard sends an unauthenticated cold start to
    // /login, so the operator login surface is shown.
    await tester.pumpWidget(const ProviderScope(child: OperatorApp()));
    await tester.pumpAndSettle();

    expect(find.text('운영자 콘솔'), findsOneWidget);
  });
}
