// Widget tests for AssenSearchField (default / focused). The clear button only
// appears with text. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenSearchField', () {
    testWidgets('renders the search icon', (tester) async {
      await tester.pumpWidget(
        _host(AssenSearchField(controller: TextEditingController())),
      );
      expect(find.byIcon(Icons.search), findsOneWidget);
    });

    testWidgets('hides the clear button when empty', (tester) async {
      await tester.pumpWidget(
        _host(AssenSearchField(controller: TextEditingController())),
      );
      expect(find.byIcon(Icons.close), findsNothing);
    });

    testWidgets('clears text and fires onClear on tap', (tester) async {
      final controller = TextEditingController(text: '미오');
      var cleared = false;
      await tester.pumpWidget(
        _host(
          AssenSearchField(
            controller: controller,
            onClear: () => cleared = true,
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.close));
      await tester.pump();
      expect(controller.text, isEmpty);
      expect(cleared, isTrue);
    });
  });

  goldenTest(
    'search field matches the approved baseline',
    fileName: 'search_field',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-text',
          child: SizedBox(
            width: 240,
            child: AssenSearchField(
              controller: TextEditingController(text: '미오'),
            ),
          ),
        ),
      ],
    ),
  );
}
