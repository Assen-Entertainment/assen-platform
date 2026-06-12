import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/molecules/notice_bar.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/molecules/segmented_tabs.dart';
import 'package:ui_kit/src/molecules/stat_card.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/reservation_card.dart';

/// The operator dashboard screen skeleton (`T5 운영자 대시보드`).
///
/// Covers the Templates/T5 row of `components.md` and the operator dashboard
/// (screens.md O1). It assembles an [AssenAppBar], a 신고 알림 [AssenNoticeBar],
/// [AssenSegmentedTabs] to switch operator views (현황/예약), a grid of
/// [AssenStatCard] daily metrics, and the 예약/대기 board as an
/// [AssenReservationCard] list. The body scrolls (a [CustomScrollView]).
///
/// Content is placeholder data — daily figures are NOT approved values
/// (screens.md mock rule; Development_Constraints: operator-internal only, no
/// public exposure). It is surfaced via constructor parameters so the real
/// console overrides it.
class AssenOperatorDashboardTemplate extends StatefulWidget {
  /// Creates the operator dashboard template.
  ///
  /// [stats] are the metric cards (a 2-column grid). [reservations] are the
  /// 예약/대기 board rows. [segments] label the view switch. The `on*` callbacks
  /// are optional (the gallery passes no-ops).
  const AssenOperatorDashboardTemplate({
    this.stats = _defaultStats,
    this.reservations = _defaultReservations,
    this.segments = const ['현황', '예약'],
    this.onBack,
    super.key,
  });

  /// The daily metric cards.
  final List<AssenDashboardStat> stats;

  /// The 예약/대기 board rows.
  final List<AssenDashboardReservation> reservations;

  /// The segmented view-switch labels.
  final List<String> segments;

  /// Optional back handler.
  final VoidCallback? onBack;

  /// The unified placeholder metrics (internal figures — not approved values).
  static const List<AssenDashboardStat> _defaultStats = [
    AssenDashboardStat(
      value: '38',
      label: '오늘 방문',
      delta: '+12%',
      trend: AssenStatTrend.up,
      icon: Icons.login_outlined,
    ),
    AssenDashboardStat(
      value: '12',
      label: '예약',
      delta: '+3',
      trend: AssenStatTrend.up,
      icon: Icons.event_available_outlined,
    ),
    AssenDashboardStat(
      value: '27',
      label: '체키 발행',
      icon: Icons.photo_camera_outlined,
    ),
    AssenDashboardStat(
      value: '1',
      label: '신고 대기',
      delta: '−1',
      trend: AssenStatTrend.down,
      icon: Icons.shield_outlined,
    ),
  ];

  /// The unified placeholder 예약/대기 board.
  static const List<AssenDashboardReservation> _defaultReservations = [
    AssenDashboardReservation(
      venue: '체리체리 · HK-0042',
      dateTime: '6월 14일 (토) 15:00',
      partySize: '2명',
      status: AssenReservationStatus.upcoming,
      ddayLabel: 'D-2',
    ),
    AssenDashboardReservation(
      venue: '유키 지명 · HK-0108',
      dateTime: '6월 12일 (목) 18:30',
      partySize: '1명',
      status: AssenReservationStatus.upcoming,
      ddayLabel: '오늘 방문',
    ),
    AssenDashboardReservation(
      venue: '모카 지명 · HK-0091',
      dateTime: '6월 11일 (수) 13:00',
      partySize: '3명',
      status: AssenReservationStatus.visited,
    ),
  ];

  @override
  State<AssenOperatorDashboardTemplate> createState() =>
      _AssenOperatorDashboardTemplateState();
}

class _AssenOperatorDashboardTemplateState
    extends State<AssenOperatorDashboardTemplate> {
  int _segment = 0;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final showStats = _segment == 0;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: '운영자 대시보드',
        onBack: widget.onBack,
        actions: [
          AssenIconButton(
            icon: Icons.settings_outlined,
            semanticLabel: '설정',
            onPressed: () {},
          ),
        ],
      ),
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s4,
              SpacingTokens.screenMargin,
              SpacingTokens.s8,
            ),
            sliver: SliverList.list(
              children: [
                const AssenNoticeBar(
                  message: '신고 1건이 접수되어 처리 대기 중입니다.',
                  kind: AssenNoticeKind.warning,
                ),
                const SizedBox(height: SpacingTokens.s4),
                AssenSegmentedTabs(
                  segments: widget.segments,
                  selectedIndex: _segment,
                  onChanged: (i) => setState(() => _segment = i),
                ),
                const SizedBox(height: SpacingTokens.s5),
                if (showStats) ...[
                  const AssenSectionHeader(title: '오늘 현황'),
                  const SizedBox(height: SpacingTokens.s3),
                  _StatGrid(stats: widget.stats),
                  const SizedBox(height: SpacingTokens.s6),
                ],
                AssenSectionHeader(
                  title: '예약 · 대기',
                  actionLabel: '전체보기',
                  onAction: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                for (final res in widget.reservations) ...[
                  AssenReservationCard(
                    venue: res.venue,
                    dateTime: res.dateTime,
                    partySize: res.partySize,
                    status: res.status,
                    ddayLabel: res.ddayLabel,
                    primaryLabel: res.status == AssenReservationStatus.upcoming
                        ? '체크인'
                        : null,
                    onPrimary: res.status == AssenReservationStatus.upcoming
                        ? () {}
                        : null,
                  ),
                  const SizedBox(height: SpacingTokens.s3),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The 2-column metric grid.
class _StatGrid extends StatelessWidget {
  const _StatGrid({required this.stats});

  final List<AssenDashboardStat> stats;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: SpacingTokens.s3,
        crossAxisSpacing: SpacingTokens.s3,
        // Metric tiles: label row + value + delta. Kept tall enough that the
        // StatCard column fits at a 2-up phone width (no vertical overflow).
        childAspectRatio: 1.2,
      ),
      itemCount: stats.length,
      itemBuilder: (context, index) {
        final stat = stats[index];
        return AssenStatCard(
          value: stat.value,
          label: stat.label,
          delta: stat.delta,
          trend: stat.trend,
          icon: stat.icon,
        );
      },
    );
  }
}

/// A daily metric for the [AssenOperatorDashboardTemplate] grid.
class AssenDashboardStat {
  /// Creates a dashboard metric.
  const AssenDashboardStat({
    required this.value,
    required this.label,
    this.delta,
    this.trend = AssenStatTrend.none,
    this.icon,
  });

  /// The metric value, pre-formatted.
  final String value;

  /// The metric name.
  final String label;

  /// Optional change caption.
  final String? delta;

  /// The trend direction for [delta].
  final AssenStatTrend trend;

  /// Optional leading glyph.
  final IconData? icon;
}

/// A 예약/대기 board row for the [AssenOperatorDashboardTemplate].
class AssenDashboardReservation {
  /// Creates a dashboard reservation row.
  const AssenDashboardReservation({
    required this.venue,
    required this.dateTime,
    required this.partySize,
    required this.status,
    this.ddayLabel,
  });

  /// The booking title (cast/member reference).
  final String venue;

  /// The formatted date/time.
  final String dateTime;

  /// The formatted party size.
  final String partySize;

  /// The reservation status.
  final AssenReservationStatus status;

  /// The visit-centric D-day caption (upcoming only).
  final String? ddayLabel;
}
