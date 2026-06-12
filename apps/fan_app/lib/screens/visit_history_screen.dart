import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

final Provider<_VisitHistoryViewData> _visitHistoryProvider =
    Provider<_VisitHistoryViewData>((ref) {
      final entries = _mockVisitEntries
          .where((entry) => entry.status == _VisitStatus.valid)
          .toList();

      return _VisitHistoryViewData(
        summary: AssenVisitHistorySummary(
          totalVisits: entries.length,
          headline: '${entries.length}번의 귀가',
          caption: '첫 방문 2026.03.14 · 최애 미오',
        ),
        monthGroups: [
          _monthGroup('6월', entries),
          _monthGroup('5월', entries),
          _monthGroup('3월', entries),
        ].where((group) => group.entries.isNotEmpty).toList(),
      );
    });

/// The fan-facing visit history screen (E2).
///
/// This read-only P0 surface uses local synthetic data and filters voided rows
/// before handing data to the shared template.
class VisitHistoryScreen extends ConsumerWidget {
  /// Creates the visit history screen.
  const VisitHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(_visitHistoryProvider);

    return AssenVisitHistoryTemplate(
      summary: data.summary,
      monthGroups: data.monthGroups,
      onBack: () => context.go(FanRoutes.my),
    );
  }
}

AssenVisitHistoryMonthGroup _monthGroup(
  String monthLabel,
  List<_VisitEntry> entries,
) {
  return AssenVisitHistoryMonthGroup(
    monthLabel: monthLabel,
    entries: entries
        .where((entry) => entry.monthLabel == monthLabel)
        .map(
          (entry) => AssenVisitHistoryEntry(
            title: entry.title,
            dateLabel: entry.dateLabel,
            trailingLabel: entry.trailingLabel,
            kind: entry.kind,
            isFirstVisit: entry.isFirstVisit,
          ),
        )
        .toList(),
  );
}

class _VisitHistoryViewData {
  const _VisitHistoryViewData({
    required this.summary,
    required this.monthGroups,
  });

  final AssenVisitHistorySummary summary;
  final List<AssenVisitHistoryMonthGroup> monthGroups;
}

enum _VisitStatus { valid, voided }

class _VisitEntry {
  const _VisitEntry({
    required this.monthLabel,
    required this.title,
    required this.dateLabel,
    required this.trailingLabel,
    required this.kind,
    this.status = _VisitStatus.valid,
    this.isFirstVisit = false,
  });

  final String monthLabel;
  final String title;
  final String dateLabel;
  final String trailingLabel;
  final AssenVisitHistoryEntryKind kind;
  final _VisitStatus status;
  final bool isFirstVisit;
}

const List<_VisitEntry> _mockVisitEntries = [
  _VisitEntry(
    monthLabel: '6월',
    title: '12번째 방문 · 미오와 체키',
    dateLabel: '6월 11일 (수)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '6월',
    title: '11번째 방문 · 유키와 체키',
    dateLabel: '6월 4일 (수)',
    trailingLabel: '−1장',
    kind: AssenVisitHistoryEntryKind.chekiTicket,
  ),
  _VisitEntry(
    monthLabel: '6월',
    title: '무효 처리된 방문 · 테스트',
    dateLabel: '6월 1일 (월)',
    trailingLabel: '+0 P',
    kind: AssenVisitHistoryEntryKind.point,
    status: _VisitStatus.voided,
  ),
  _VisitEntry(
    monthLabel: '5월',
    title: '10번째 방문 · 미오와 보드게임',
    dateLabel: '5월 28일 (수)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '5월',
    title: '9번째 방문 · 유키와 체키',
    dateLabel: '5월 14일 (수)',
    trailingLabel: '−1장',
    kind: AssenVisitHistoryEntryKind.chekiTicket,
  ),
  _VisitEntry(
    monthLabel: '5월',
    title: '8번째 방문 · 미오와 체키',
    dateLabel: '5월 7일 (수)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '7번째 방문 · 미오와 체키',
    dateLabel: '3월 28일 (토)',
    trailingLabel: '−1장',
    kind: AssenVisitHistoryEntryKind.chekiTicket,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '6번째 방문 · 유키와 체키',
    dateLabel: '3월 26일 (목)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '5번째 방문 · 미오와 체키',
    dateLabel: '3월 24일 (화)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '4번째 방문 · 유키와 체키',
    dateLabel: '3월 21일 (토)',
    trailingLabel: '−1장',
    kind: AssenVisitHistoryEntryKind.chekiTicket,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '3번째 방문 · 미오와 체키',
    dateLabel: '3월 19일 (목)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '2번째 방문 · 유키와 체키',
    dateLabel: '3월 16일 (월)',
    trailingLabel: '−1장',
    kind: AssenVisitHistoryEntryKind.chekiTicket,
  ),
  _VisitEntry(
    monthLabel: '3월',
    title: '1번째 방문 · 미오와 체키',
    dateLabel: '3월 14일 (토)',
    trailingLabel: '+50 P',
    kind: AssenVisitHistoryEntryKind.point,
    isFirstVisit: true,
  ),
];
