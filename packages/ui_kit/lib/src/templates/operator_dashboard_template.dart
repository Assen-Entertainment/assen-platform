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
  /// 예약/대기 board rows. [segments] label the view switch. [businessDayLabel]
  /// captions which day the metrics describe. [noticeMessage] is the 신고 알림
  /// strip text; [onNoticeTap] makes it a status-edit entry point when set.
  /// [quickActions] are status-edit entry points; [adminActions] are the
  /// admin-only sections (the caller gates these by role — empty hides the
  /// section). [onExportCsv] surfaces the CSV export action when set. The `on*`
  /// callbacks are optional (the gallery passes none).
  const AssenOperatorDashboardTemplate({
    this.stats = _defaultStats,
    this.reservations = _defaultReservations,
    this.segments = const ['현황', '예약'],
    this.businessDayLabel,
    this.noticeMessage = _defaultNotice,
    this.onNoticeTap,
    this.quickActions = const <AssenDashboardQuickAction>[],
    this.adminActions = const <AssenDashboardQuickAction>[],
    this.onExportCsv,
    this.onBack,
    super.key,
  });

  /// The daily metric cards.
  final List<AssenDashboardStat> stats;

  /// The 예약/대기 board rows.
  final List<AssenDashboardReservation> reservations;

  /// The segmented view-switch labels.
  final List<String> segments;

  /// Optional caption for the day the [stats] describe (e.g. an ISO date).
  final String? businessDayLabel;

  /// The 신고 알림 strip message.
  final String noticeMessage;

  /// Optional tap handler turning the notice into a status-edit entry point.
  final VoidCallback? onNoticeTap;

  /// Status-edit console entry points, rendered as a 바로가기 action row.
  final List<AssenDashboardQuickAction> quickActions;

  /// Admin-only section entry points (settings / permissions / risk / audit).
  ///
  /// The caller decides visibility by role; an empty list hides the 관리
  /// section entirely (the fail-closed default for an operator viewer).
  final List<AssenDashboardQuickAction> adminActions;

  /// Optional CSV-export handler (a download action in the app bar when set).
  final VoidCallback? onExportCsv;

  /// Optional back handler.
  final VoidCallback? onBack;

  /// The default 신고 알림 strip text (overridden with the live backlog count).
  static const String _defaultNotice = '처리 대기 중인 신고를 확인하세요.';

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
          if (widget.onExportCsv != null)
            AssenIconButton(
              icon: Icons.download_outlined,
              semanticLabel: 'CSV 내보내기',
              onPressed: widget.onExportCsv,
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
                _Notice(
                  message: widget.noticeMessage,
                  onTap: widget.onNoticeTap,
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
                  if (widget.businessDayLabel != null) ...[
                    const SizedBox(height: SpacingTokens.s1),
                    Text(
                      '${widget.businessDayLabel!} 기준',
                      style: TextStyle(
                        color: colors.ink500,
                        fontSize: TypographyTokens.bodySSize,
                      ),
                    ),
                  ],
                  const SizedBox(height: SpacingTokens.s3),
                  _StatGrid(stats: widget.stats),
                  if (widget.quickActions.isNotEmpty) ...[
                    const SizedBox(height: SpacingTokens.s6),
                    const AssenSectionHeader(title: '바로가기'),
                    const SizedBox(height: SpacingTokens.s3),
                    _QuickActionRow(actions: widget.quickActions),
                  ],
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
                if (showStats && widget.adminActions.isNotEmpty) ...[
                  const SizedBox(height: SpacingTokens.s5),
                  const AssenSectionHeader(title: '관리'),
                  const SizedBox(height: SpacingTokens.s3),
                  for (final action in widget.adminActions) ...[
                    _AdminRow(action: action),
                    const SizedBox(height: SpacingTokens.s2),
                  ],
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

/// The 신고 알림 strip, optionally tappable as a status-edit entry point.
class _Notice extends StatelessWidget {
  const _Notice({required this.message, this.onTap});

  final String message;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final notice = AssenNoticeBar(
      message: message,
      kind: AssenNoticeKind.warning,
    );
    if (onTap == null) return notice;
    return InkWell(
      onTap: onTap,
      borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
      child: notice,
    );
  }
}

/// The 바로가기 row of status-edit console entry points.
class _QuickActionRow extends StatelessWidget {
  const _QuickActionRow({required this.actions});

  final List<AssenDashboardQuickAction> actions;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: SpacingTokens.s3,
      runSpacing: SpacingTokens.s3,
      children: [
        for (final action in actions)
          OutlinedButton.icon(
            onPressed: action.onTap,
            icon: Icon(action.icon, size: SpacingTokens.s4),
            label: Text(action.label),
          ),
      ],
    );
  }
}

/// One admin-only section row (icon + label + chevron); manager-gated upstream.
class _AdminRow extends StatelessWidget {
  const _AdminRow({required this.action});

  final AssenDashboardQuickAction action;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Material(
      color: colors.white,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: colors.ink100),
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
      ),
      child: InkWell(
        onTap: action.onTap,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
        child: Padding(
          padding: const EdgeInsets.all(SpacingTokens.s3),
          child: Row(
            children: [
              Icon(action.icon, size: SpacingTokens.s5, color: colors.ink700),
              const SizedBox(width: SpacingTokens.s3),
              Expanded(
                child: Text(
                  action.label,
                  style: TextStyle(
                    color: colors.ink900,
                    fontSize: TypographyTokens.bodyMSize,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Icon(
                Icons.chevron_right,
                size: SpacingTokens.s5,
                color: colors.ink500,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A status-edit / admin entry point on the [AssenOperatorDashboardTemplate].
class AssenDashboardQuickAction {
  /// Creates a dashboard entry point.
  const AssenDashboardQuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  /// The leading glyph.
  final IconData icon;

  /// The action label.
  final String label;

  /// Invoked when the entry point is tapped (typically a navigation).
  final VoidCallback onTap;
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
