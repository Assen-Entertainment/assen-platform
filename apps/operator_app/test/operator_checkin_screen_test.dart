import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/screens/operator_checkin_screen.dart';
import 'package:ui_kit/ui_kit.dart';

Future<void> _pump(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        theme: AssenTheme.light(),
        home: const OperatorCheckinScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders today visit list with status badges', (tester) async {
    await _pump(tester);

    expect(find.text('체크인'), findsOneWidget);
    expect(find.text('하루'), findsOneWidget);
    expect(find.text('미오'), findsOneWidget);
    expect(find.text('방문'), findsOneWidget);
    expect(find.text('무효'), findsOneWidget);
  });

  testWidgets('manual check-in adds a visit row', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('수동 체크인'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();

    expect(find.text('하루'), findsNWidgets(2));
  });

  testWidgets('void action requires a reason dialog and marks row voided', (
    tester,
  ) async {
    await _pump(tester);

    final voidButtons = find.byIcon(Icons.block_outlined);
    await tester.tap(voidButtons.at(1));
    await tester.pumpAndSettle();

    expect(find.text('방문 무효'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '중복 체크인');
    await tester.tap(find.widgetWithText(FilledButton, '무효'));
    await tester.pumpAndSettle();

    expect(find.text('무효'), findsNWidgets(2));
  });

  testWidgets('voided rows use strikethrough styling', (tester) async {
    await _pump(tester);

    final text = tester.widget<Text>(find.text('미오'));
    expect(text.style?.decoration, TextDecoration.lineThrough);
  });
}
