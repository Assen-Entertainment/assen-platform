import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/main.dart';

void main() {
  testWidgets('OperatorApp boots and shows the placeholder dashboard', (
    tester,
  ) async {
    // OperatorApp embeds a ConsumerWidget, so it needs a ProviderScope
    // ancestor.
    await tester.pumpWidget(const ProviderScope(child: OperatorApp()));

    expect(find.text('Operator Console'), findsOneWidget);
  });
}
