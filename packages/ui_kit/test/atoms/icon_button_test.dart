// Widget tests for AssenIconButton. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenIconButton', () {
    testWidgets('renders the glyph', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenIconButton(
            icon: Icons.close,
            semanticLabel: '닫기',
            onPressed: () {},
          ),
        ),
      );
      expect(find.byIcon(Icons.close), findsOneWidget);
    });

    testWidgets('fires onPressed', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenIconButton(
            icon: Icons.share,
            semanticLabel: '공유',
            onPressed: () => taps++,
          ),
        ),
      );
      await tester.tap(find.byType(AssenIconButton));
      expect(taps, 1);
    });

    testWidgets('disabled when onPressed is null', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenIconButton(
            icon: Icons.settings,
            semanticLabel: '설정',
            onPressed: null,
          ),
        ),
      );
      final button = tester.widget<IconButton>(find.byType(IconButton));
      expect(button.onPressed, isNull);
    });

    testWidgets('meets the 48dp minimum touch target', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenIconButton(
            icon: Icons.close,
            semanticLabel: '닫기',
            onPressed: () {},
          ),
        ),
      );
      final size = tester.getSize(find.byType(IconButton));
      expect(size.width, greaterThanOrEqualTo(48));
      expect(size.height, greaterThanOrEqualTo(48));
    });
  });

  goldenTest(
    'AssenIconButton matches the approved baseline',
    fileName: 'icon_button',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'enabled',
          child: AssenIconButton(
            icon: Icons.close,
            semanticLabel: '닫기',
            onPressed: () {},
          ),
        ),
        GoldenTestScenario(
          name: 'disabled',
          child: const AssenIconButton(
            icon: Icons.settings,
            semanticLabel: '설정',
            onPressed: null,
          ),
        ),
      ],
    ),
  );
}
