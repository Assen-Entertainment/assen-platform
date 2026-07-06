// Widget tests for AssenProductCard: title/price/tag/meta render and onTap
// fires. Golden skip #31.

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
  group('AssenProductCard', () {
    testWidgets('renders the title, price, tag, and meta', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenProductCard(
            title: '한정 아크릴 스탠드',
            priceLabel: '₩18,000',
            tagLabel: '굿즈',
            meta: '선착순 100개',
          ),
        ),
      );
      expect(find.text('한정 아크릴 스탠드'), findsOneWidget);
      expect(find.text('₩18,000'), findsOneWidget);
      expect(find.text('굿즈'), findsOneWidget);
      expect(find.text('선착순 100개'), findsOneWidget);
    });

    testWidgets('fires onTap when tapped', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenProductCard(
            title: '스탠드',
            priceLabel: '₩18,000',
            onTap: () => taps++,
          ),
        ),
      );
      await tester.tap(find.text('스탠드'));
      expect(taps, 1);
    });
  });
}
