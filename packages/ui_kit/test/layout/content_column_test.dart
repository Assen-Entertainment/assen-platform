import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void _setWideViewport(WidgetTester tester) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(2000, 900);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  group('AssenContentColumn maxWidth', () {
    testWidgets('honours a custom (console) maxWidth', (tester) async {
      _setWideViewport(tester);

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AssenContentColumn(
              maxWidth: AssenLayout.consoleContentMaxWidth,
              child: SizedBox.expand(key: Key('wide-child')),
            ),
          ),
        ),
      );

      expect(
        tester.getSize(find.byKey(const Key('wide-child'))).width,
        AssenLayout.consoleContentMaxWidth,
      );
    });

    testWidgets('defaults to the fan reading column', (tester) async {
      _setWideViewport(tester);

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AssenContentColumn(
              child: SizedBox.expand(key: Key('default-child')),
            ),
          ),
        ),
      );

      expect(
        tester.getSize(find.byKey(const Key('default-child'))).width,
        AssenLayout.contentMaxWidth,
      );
    });
  });
}
