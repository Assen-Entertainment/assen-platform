import 'package:fan_app/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('FanApp boots into the onboarding entry point (P3a router)', (
    tester,
  ) async {
    // FanApp is a ConsumerWidget driving MaterialApp.router; it needs a
    // ProviderScope ancestor. kIsWeb is false under `flutter test`, so the
    // first entry is /onboarding (§4.3 모바일 첫 진입); the web entry (/login)
    // and the auth guard are asserted in router_test.dart.
    await tester.pumpWidget(const ProviderScope(child: FanApp()));
    await tester.pumpAndSettle();

    expect(find.text('이미 계정이 있어요'), findsOneWidget);
  });
}
