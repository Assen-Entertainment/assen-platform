import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void _setViewport(WidgetTester tester, Size size) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = size;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  group('AssenFormFrame', () {
    testWidgets('caps the body to formMaxWidth on wide viewports', (
      tester,
    ) async {
      _setViewport(tester, const Size(2000, 900));

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AssenFormFrame(
              child: SizedBox.expand(key: Key('form-child')),
            ),
          ),
        ),
      );

      expect(
        tester.getSize(find.byKey(const Key('form-child'))).width,
        AssenLayout.formMaxWidth,
      );
    });

    testWidgets(
      'falls back to screen-margin gutters when narrower than the cap',
      (tester) async {
        const width = 360.0;
        _setViewport(tester, const Size(width, 900));

        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: AssenFormFrame(
                child: SizedBox.expand(key: Key('form-child')),
              ),
            ),
          ),
        );

        expect(
          tester.getSize(find.byKey(const Key('form-child'))).width,
          width - SpacingTokens.screenMargin * 2,
        );
      },
    );

    testWidgets('preserves height constraints so Expanded children lay out', (
      tester,
    ) async {
      _setViewport(tester, const Size(2000, 900));

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AssenFormFrame(
              child: Column(
                children: [
                  Expanded(child: SizedBox.expand(key: Key('tall-child'))),
                ],
              ),
            ),
          ),
        ),
      );

      expect(tester.takeException(), isNull);
      expect(
        tester.getSize(find.byKey(const Key('tall-child'))).height,
        900,
      );
    });
  });
}
