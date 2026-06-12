import 'package:fan_app/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('FanApp boots into the login entry point (P3a router)', (
    tester,
  ) async {
    // FanApp is a ConsumerWidget driving MaterialApp.router; it needs a
    // ProviderScope ancestor. The guard sends an unauthenticated cold start to
    // /login (the Flutter web entry point), so the login surface is shown.
    await tester.pumpWidget(const ProviderScope(child: FanApp()));
    await tester.pumpAndSettle();

    expect(find.text('로그인'), findsOneWidget);
  });
}
