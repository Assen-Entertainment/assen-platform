// Widget tests for AssenStatRow: renders each value/label pair. Golden skip #31.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenStatRow', () {
    testWidgets('renders each stat value and label', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatRow(
            stats: [
              AssenStat(value: '1,284', label: '팔로워'),
              AssenStat(value: '37', label: '게시물'),
            ],
          ),
        ),
      );
      expect(find.text('1,284'), findsOneWidget);
      expect(find.text('팔로워'), findsOneWidget);
      expect(find.text('37'), findsOneWidget);
      expect(find.text('게시물'), findsOneWidget);
    });

    testWidgets('renders a single stat without a divider', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenStatRow(
            stats: [AssenStat(value: '5', label: '게시물')],
          ),
        ),
      );
      expect(find.text('5'), findsOneWidget);
      expect(find.text('게시물'), findsOneWidget);
    });
  });
}
