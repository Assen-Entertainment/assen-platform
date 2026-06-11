import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('PlaceholderFeatureScreen renders the provided greeting', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: PlaceholderFeatureScreen()),
      ),
    );

    expect(find.text('Assen Platform'), findsOneWidget);
  });
}
