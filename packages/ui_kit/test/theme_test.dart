import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenTheme', () {
    test('builds a Material 3 light theme', () {
      final theme = AssenTheme.light();
      expect(theme.useMaterial3, isTrue);
      expect(theme.colorScheme.brightness, Brightness.light);
    });

    testWidgets('applies to a MaterialApp without error', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const Scaffold(body: Text('Assen')),
        ),
      );
      expect(find.text('Assen'), findsOneWidget);
    });
  });
}
