import 'package:fan_app/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('FanApp boots and shows the placeholder feature', (tester) async {
    // FanApp embeds a ConsumerWidget, so it needs a ProviderScope ancestor —
    // main() supplies one in production; the test supplies it here.
    await tester.pumpWidget(const ProviderScope(child: FanApp()));

    expect(find.text('Assen Platform'), findsOneWidget);
  });
}
