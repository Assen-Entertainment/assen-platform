// Widget tests for AssenBannerCard (홈 배너). Renders title/subtitle over the
// background and fires onTap. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 320, child: child)),
  ),
);

void main() {
  group('AssenBannerCard', () {
    testWidgets('renders title and subtitle', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenBannerCard(
            title: '6월 콜라보',
            subtitle: '한정 체키 증정',
            background: ColoredBox(color: Color(0xFFE2DAF4)),
          ),
        ),
      );
      expect(find.text('6월 콜라보'), findsOneWidget);
      expect(find.text('한정 체키 증정'), findsOneWidget);
    });

    testWidgets('fires onTap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _host(
          AssenBannerCard(
            title: '6월 콜라보',
            background: const ColoredBox(color: Color(0xFFE2DAF4)),
            onTap: () => tapped = true,
          ),
        ),
      );
      await tester.tap(find.text('6월 콜라보'));
      expect(tapped, isTrue);
    });
  });

  goldenTest(
    'banner card matches the approved baseline',
    fileName: 'banner_card',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-subtitle',
          child: const SizedBox(
            width: 320,
            child: AssenBannerCard(
              title: '6월 콜라보 이벤트',
              subtitle: '한정 체키 증정',
              background: ColoredBox(color: Color(0xFFE2DAF4)),
            ),
          ),
        ),
      ],
    ),
  );
}
