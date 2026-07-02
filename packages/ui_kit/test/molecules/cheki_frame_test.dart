// Widget tests for AssenChekiFrame (체키 54:86). Holds the 54:86 film ratio,
// shows the image slot and the optional caption. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenChekiFrame', () {
    testWidgets('renders the caption', (tester) async {
      await tester.pumpWidget(
        _host(
          const SizedBox(
            width: 140,
            child: AssenChekiFrame(
              image: ColoredBox(color: Color(0xFFFFD9E2)),
              caption: 'first cheki',
            ),
          ),
        ),
      );
      expect(find.text('first cheki'), findsOneWidget);
    });

    testWidgets('keeps the 54:86 film aspect ratio', (tester) async {
      await tester.pumpWidget(
        _host(
          const SizedBox(
            width: 140,
            child: AssenChekiFrame(
              image: ColoredBox(color: Color(0xFFFFD9E2)),
            ),
          ),
        ),
      );
      final ratio = tester.widget<AspectRatio>(
        find.byType(AspectRatio).first,
      );
      expect(ratio.aspectRatio, closeTo(54 / 86, 0.0001));
    });
  });

  goldenTest(
    'cheki frame matches the approved baseline',
    fileName: 'cheki_frame',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-caption',
          child: const SizedBox(
            width: 140,
            child: AssenChekiFrame(
              image: ColoredBox(color: Color(0xFFFFD9E2)),
              caption: 'first cheki ♥',
            ),
          ),
        ),
      ],
    ),
  );
}
