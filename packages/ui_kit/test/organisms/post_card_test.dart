// Widget tests for AssenPostCard: the creator row, body and like/comment counts
// render, and onTap fires. Golden skip #31.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 360, child: child)),
  ),
);

void main() {
  group('AssenPostCard', () {
    testWidgets('renders the creator, body, and counts', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenPostCard(
            creatorName: '미오',
            creatorMeta: '@mio',
            timeLabel: '3시간 전',
            verified: true,
            body: '오늘 방송 고마웠어요!',
            likeCount: 128,
            commentCount: 16,
          ),
        ),
      );

      expect(find.text('미오'), findsOneWidget);
      expect(find.text('@mio'), findsOneWidget);
      expect(find.text('오늘 방송 고마웠어요!'), findsOneWidget);
      expect(find.text('128'), findsOneWidget);
      expect(find.text('16'), findsOneWidget);
      expect(find.byIcon(Icons.verified), findsOneWidget);
    });

    testWidgets('fires onTap when tapped', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenPostCard(
            creatorName: '미오',
            body: '안녕하세요',
            onTap: () => taps++,
          ),
        ),
      );
      await tester.tap(find.text('안녕하세요'));
      expect(taps, 1);
    });

    testWidgets('shows a filled heart when liked', (tester) async {
      await tester.pumpWidget(
        _host(const AssenPostCard(creatorName: '미오', liked: true)),
      );
      expect(find.byIcon(Icons.favorite), findsOneWidget);
      expect(find.byIcon(Icons.favorite_border), findsNothing);
    });
  });
}
