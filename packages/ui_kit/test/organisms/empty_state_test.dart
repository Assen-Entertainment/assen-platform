// Widget tests for AssenEmptyState. Copy, optional illustration slot, and the
// optional recovery CTA (action vs. no-action). Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenEmptyState', () {
    testWidgets('renders title and message', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenEmptyState(
            title: '아직 모은 체키가 없어요',
            message: '방문하고 체키를 받으면 이곳에 모여요.',
          ),
        ),
      );
      expect(find.text('아직 모은 체키가 없어요'), findsOneWidget);
      expect(find.text('방문하고 체키를 받으면 이곳에 모여요.'), findsOneWidget);
    });

    testWidgets('shows no CTA when actionLabel is omitted', (tester) async {
      await tester.pumpWidget(
        _host(const AssenEmptyState(title: '비어 있음', message: '내용 없음')),
      );
      expect(find.byType(AssenButton), findsNothing);
    });

    testWidgets('renders and fires the recovery CTA', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenEmptyState(
            title: '예약이 없어요',
            message: '지금 예약해 보세요.',
            actionLabel: '예약하기',
            onAction: () => taps++,
          ),
        ),
      );
      expect(find.text('예약하기'), findsOneWidget);
      await tester.tap(find.text('예약하기'));
      expect(taps, 1);
    });

    testWidgets('renders the illustration slot', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenEmptyState(
            title: '비어 있음',
            message: '내용 없음',
            slot: Icon(Icons.photo_library_outlined),
          ),
        ),
      );
      expect(find.byIcon(Icons.photo_library_outlined), findsOneWidget);
    });
  });

  goldenTest(
    'empty state matches the approved baseline',
    fileName: 'empty_state',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-cta',
          child: SizedBox(
            width: 360,
            height: 360,
            child: AssenEmptyState(
              title: '아직 모은 체키가 없어요',
              message: '방문하고 체키를 받으면 이곳에 모여요.',
              slot: const Icon(Icons.photo_library_outlined, size: 48),
              actionLabel: '캐스트 보러 가기',
              onAction: () {},
            ),
          ),
        ),
      ],
    ),
  );
}
