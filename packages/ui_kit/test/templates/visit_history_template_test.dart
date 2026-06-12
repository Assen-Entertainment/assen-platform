// Smoke + structure test for the E2 visit history template. The pixel golden
// is declared but skipped (CONSTRAINTS #31, human-gated baseline).

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenVisitHistoryTemplate', () {
    testWidgets('renders summary, month groups, first badge, and deltas', (
      tester,
    ) async {
      _useTallSurface(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: const AssenVisitHistoryTemplate(
            summary: AssenVisitHistorySummary(
              totalVisits: 12,
              headline: '12번의 귀가',
              caption: '첫 방문 2026.03.14 · 최애 미오',
            ),
            monthGroups: [
              AssenVisitHistoryMonthGroup(
                monthLabel: '6월',
                entries: [
                  AssenVisitHistoryEntry(
                    title: '12번째 방문 · 미오와 체키',
                    dateLabel: '6월 11일 (수)',
                    trailingLabel: '+50 P',
                    kind: AssenVisitHistoryEntryKind.point,
                  ),
                  AssenVisitHistoryEntry(
                    title: '11번째 방문 · 유키와 체키',
                    dateLabel: '6월 4일 (수)',
                    trailingLabel: '−1장',
                    kind: AssenVisitHistoryEntryKind.chekiTicket,
                  ),
                ],
              ),
              AssenVisitHistoryMonthGroup(
                monthLabel: '5월',
                entries: [
                  AssenVisitHistoryEntry(
                    title: '1번째 방문 · 미오와 체키',
                    dateLabel: '5월 1일 (금)',
                    trailingLabel: '+50 P',
                    kind: AssenVisitHistoryEntryKind.point,
                    isFirstVisit: true,
                  ),
                ],
              ),
            ],
          ),
        ),
      );

      expect(find.text('나의 하츠코이 기록'), findsOneWidget);
      expect(find.byType(AssenProgressDonut), findsOneWidget);
      expect(find.text('12회'), findsOneWidget);
      expect(find.text('12번의 귀가'), findsOneWidget);
      expect(find.text('첫 방문 2026.03.14 · 최애 미오'), findsOneWidget);
      expect(find.text('6월'), findsOneWidget);
      expect(find.text('5월'), findsOneWidget);
      expect(find.text('첫 방문'), findsOneWidget);

      final positiveText = tester.widget<Text>(find.text('+50 P').first);
      final neutralText = tester.widget<Text>(find.text('−1장'));
      const colors = AssenColors();
      expect(positiveText.style?.color, colors.matchaInk);
      expect(neutralText.style?.color, colors.ink700);
    });

    goldenTest(
      'visit history template matches the approved baseline',
      fileName: 'visit_history_template',
      skip: true,
      builder: () => GoldenTestGroup(
        children: [
          GoldenTestScenario(
            name: 'default',
            child: const SizedBox(
              width: 375,
              height: 1024,
              child: AssenVisitHistoryTemplate(
                summary: AssenVisitHistorySummary(
                  totalVisits: 12,
                  headline: '12번의 귀가',
                  caption: '첫 방문 2026.03.14 · 최애 미오',
                ),
                monthGroups: [
                  AssenVisitHistoryMonthGroup(
                    monthLabel: '6월',
                    entries: [
                      AssenVisitHistoryEntry(
                        title: '12번째 방문 · 미오와 체키',
                        dateLabel: '6월 11일 (수)',
                        trailingLabel: '+50 P',
                        kind: AssenVisitHistoryEntryKind.point,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  });
}

/// Sizes the test view so every timeline row builds without scrolling.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1125, 3600);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}
