import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenPointsHistoryTemplate', () {
    testWidgets('renders summary, groups, and signed point treatments', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenPointsHistoryTemplate(
            summary: AssenPointsSummary(
              balance: 1250,
              expiryNote: '이번 달 소멸 예정 없음',
            ),
            monthGroups: [
              AssenPointsMonthGroup(
                monthLabel: '6월',
                entries: [
                  AssenPointEntry(
                    title: '12번째 방문 적립',
                    dateLabel: '6월 11일 (수)',
                    delta: 50,
                  ),
                  AssenPointEntry(
                    title: '포인트로 결제',
                    dateLabel: '6월 4일 (수)',
                    delta: -500,
                  ),
                ],
              ),
              AssenPointsMonthGroup(
                monthLabel: '5월',
                entries: [
                  AssenPointEntry(
                    title: '생탄제 이벤트 보너스',
                    dateLabel: '5월 28일 (수)',
                    delta: 200,
                  ),
                ],
              ),
            ],
          ),
        ),
      );

      expect(find.text('포인트 내역'), findsOneWidget);
      expect(find.text('보유 포인트'), findsOneWidget);
      expect(find.text('1,250 P'), findsOneWidget);
      expect(find.text('이번 달 소멸 예정 없음'), findsOneWidget);
      expect(find.text('6월'), findsOneWidget);
      expect(find.text('5월'), findsOneWidget);
      expect(find.text('+50 P'), findsOneWidget);
      expect(find.text('−500 P'), findsOneWidget);

      const colors = AssenColors();
      final positiveText = tester.widget<Text>(find.text('+50 P'));
      final negativeText = tester.widget<Text>(find.text('−500 P'));
      expect(positiveText.style?.color, colors.roseMain);
      expect(negativeText.style?.color, colors.ink900);

      final timelineItems = tester
          .widgetList<AssenTimelineItem>(find.byType(AssenTimelineItem))
          .toList();
      expect(timelineItems[0].accent, colors.roseMain);
      expect(timelineItems[1].accent, colors.ink500);
    });

    testWidgets('renders the empty-state pattern when there are no rows', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenPointsHistoryTemplate(
            summary: AssenPointsSummary(
              balance: 0,
              expiryNote: '이번 달 소멸 예정 없음',
            ),
            monthGroups: [],
          ),
        ),
      );

      expect(find.byType(AssenEmptyState), findsOneWidget);
      expect(find.text('포인트 내역이 없어요'), findsOneWidget);
      expect(find.text('적립하거나 사용한 포인트가 아직 없습니다.'), findsOneWidget);
    });
  });
}

/// Sizes the test view so every timeline row builds without scrolling.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(390, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}
