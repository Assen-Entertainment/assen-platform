import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

final Provider<_PointsHistoryViewData> _pointsHistoryProvider =
    Provider<_PointsHistoryViewData>((ref) {
      return const _PointsHistoryViewData(
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
                title: '생탄제 이벤트 보너스',
                dateLabel: '6월 8일 (일)',
                delta: 200,
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
                title: '11번째 방문 적립',
                dateLabel: '5월 28일 (수)',
                delta: 50,
              ),
              AssenPointEntry(
                title: '출석 보너스 적립',
                dateLabel: '5월 14일 (수)',
                delta: 100,
              ),
            ],
          ),
        ],
      );
    });

/// The fan-facing read-only points history screen (F3).
///
/// ASS-142 intentionally uses synthetic point-only data. Coupon value, discount
/// copy, and cash-equivalent strings are approval-gated and stay out of this
/// mock surface.
class PointsHistoryScreen extends ConsumerWidget {
  /// Creates the points history screen.
  const PointsHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(_pointsHistoryProvider);

    return AssenPointsHistoryTemplate(
      summary: data.summary,
      monthGroups: data.monthGroups,
      onBack: () => context.go(FanRoutes.my),
    );
  }
}

class _PointsHistoryViewData {
  const _PointsHistoryViewData({
    required this.summary,
    required this.monthGroups,
  });

  final AssenPointsSummary summary;
  final List<AssenPointsMonthGroup> monthGroups;
}
