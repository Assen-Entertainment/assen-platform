import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/screens/operator_cheki_screen.dart';
import 'package:ui_kit/ui_kit.dart';

Future<void> _pump(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        theme: AssenTheme.light(),
        home: const OperatorChekiScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders today cheki list with status badges', (tester) async {
    await _pump(tester);

    expect(find.text('체키 기록'), findsWidgets);
    expect(find.textContaining('미오'), findsOneWidget);
    expect(find.textContaining('유키'), findsOneWidget);
    expect(find.text('기록'), findsOneWidget);
    expect(find.text('무효'), findsOneWidget);
  });

  testWidgets('recording a cheki adds a row', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('체키 기록').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();

    // 미오 default cast → a second 미오 row appears.
    expect(find.textContaining('미오'), findsNWidgets(2));
  });

  testWidgets('void action requires a reason and marks row voided', (
    tester,
  ) async {
    await _pump(tester);

    await tester.tap(find.byIcon(Icons.block_outlined).first);
    await tester.pumpAndSettle();

    expect(find.text('체키 무효'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '중복');
    await tester.tap(find.widgetWithText(FilledButton, '무효'));
    await tester.pumpAndSettle();

    expect(find.text('무효'), findsNWidgets(2));
  });
}
