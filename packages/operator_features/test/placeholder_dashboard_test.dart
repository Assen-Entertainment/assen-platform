import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_features/operator_features.dart';

void main() {
  testWidgets('PlaceholderDashboardScreen renders the console title', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: PlaceholderDashboardScreen()),
      ),
    );

    expect(find.text('Operator Console'), findsOneWidget);
  });
}
