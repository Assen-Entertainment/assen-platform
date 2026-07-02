import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/atoms/progress.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/molecules/timeline_item.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';

/// Visit history reward/ledger kinds that need different value treatment.
enum AssenVisitHistoryEntryKind {
  /// Point grant rows use the positive accent.
  point,

  /// Cheki-ticket rows use the neutral ledger treatment.
  chekiTicket,
}

/// Summary copy for the fan-facing visit ledger.
///
/// The values are kept caller-owned so apps can filter sensitive or invalid
/// data before it reaches the shared template.
class AssenVisitHistorySummary {
  /// Creates the summary shown above the monthly timeline.
  const AssenVisitHistorySummary({
    required this.totalVisits,
    required this.headline,
    required this.caption,
  });

  /// Total valid visits after the app data layer applies exclusions.
  final int totalVisits;

  /// Short milestone line, e.g. `12번의 귀가`.
  final String headline;

  /// Secondary context, e.g. first visit and favorite cast.
  final String caption;
}

/// One valid visit row in the fan visit timeline.
class AssenVisitHistoryEntry {
  /// Creates a visit row for a monthly timeline section.
  const AssenVisitHistoryEntry({
    required this.title,
    required this.dateLabel,
    required this.trailingLabel,
    required this.kind,
    this.isFirstVisit = false,
  });

  /// Primary visit description.
  final String title;

  /// Korean date label rendered above the title.
  final String dateLabel;

  /// Ledger delta rendered at the row trailing edge.
  final String trailingLabel;

  /// Ledger kind that controls trailing emphasis.
  final AssenVisitHistoryEntryKind kind;

  /// Whether this row is the first-ever valid visit.
  final bool isFirstVisit;
}

/// A month section in reverse-chronological visit history.
class AssenVisitHistoryMonthGroup {
  /// Creates a month group with newest entries first.
  const AssenVisitHistoryMonthGroup({
    required this.monthLabel,
    required this.entries,
  });

  /// Month label, e.g. `6월`.
  final String monthLabel;

  /// Valid visit entries belonging to this month.
  final List<AssenVisitHistoryEntry> entries;
}

/// Fan-facing visit history screen template (E2).
///
/// The template owns only layout and visual semantics. The app supplies already
/// filtered data so voided visits and future backend privacy rules stay outside
/// the design-system layer.
class AssenVisitHistoryTemplate extends StatelessWidget {
  /// Creates the visit-history template.
  const AssenVisitHistoryTemplate({
    required this.summary,
    required this.monthGroups,
    this.onBack,
    super.key,
  });

  /// Valid-visit summary shown in the hero row.
  final AssenVisitHistorySummary summary;

  /// Month-grouped valid visit rows, newest first.
  final List<AssenVisitHistoryMonthGroup> monthGroups;

  /// Optional back handler for nested fan-app routes.
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '나의 하츠코이 기록', onBack: onBack),
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
                _VisitSummaryCard(summary: summary),
                const SizedBox(height: SpacingTokens.s6),
                for (final group in monthGroups) ...[
                  AssenSectionHeader(title: group.monthLabel),
                  const SizedBox(height: SpacingTokens.s3),
                  _VisitTimeline(entries: group.entries),
                  const SizedBox(height: SpacingTokens.s5),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The Scaffold-less visit-history body for embedding in a list-detail pane
/// (ASS-147 Slice 4): the same summary card + monthly visit timelines as
/// [AssenVisitHistoryTemplate] but WITHOUT a [Scaffold] or [AssenAppBar], so it
/// mounts as the detail pane of the My hub. The route-built full-Scaffold
/// template is unchanged.
class AssenVisitHistoryBody extends StatelessWidget {
  /// Creates an embeddable visit-history body.
  const AssenVisitHistoryBody({
    required this.summary,
    required this.monthGroups,
    super.key,
  });

  /// Valid-visit summary shown in the hero row.
  final AssenVisitHistorySummary summary;

  /// Month-grouped valid visit rows, newest first.
  final List<AssenVisitHistoryMonthGroup> monthGroups;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        SpacingTokens.screenMargin,
        SpacingTokens.s4,
        SpacingTokens.screenMargin,
        SpacingTokens.s8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _VisitSummaryCard(summary: summary),
          const SizedBox(height: SpacingTokens.s6),
          for (final group in monthGroups) ...[
            AssenSectionHeader(title: group.monthLabel),
            const SizedBox(height: SpacingTokens.s3),
            _VisitTimeline(entries: group.entries),
            const SizedBox(height: SpacingTokens.s5),
          ],
        ],
      ),
    );
  }
}

class _VisitSummaryCard extends StatelessWidget {
  const _VisitSummaryCard({required this.summary});

  final AssenVisitHistorySummary summary;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      child: Row(
        children: [
          AssenProgressDonut(
            value: 1,
            center: Text(
              '${summary.totalVisits}회',
              style: TypographyTokens.titleM.copyWith(
                color: colors.roseMain,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: SpacingTokens.s4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  summary.headline,
                  style: TypographyTokens.headline.copyWith(
                    color: colors.ink900,
                  ),
                ),
                const SizedBox(height: SpacingTokens.s2),
                Text(
                  summary.caption,
                  style: TypographyTokens.bodyM.copyWith(
                    color: colors.ink700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _VisitTimeline extends StatelessWidget {
  const _VisitTimeline({required this.entries});

  final List<AssenVisitHistoryEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < entries.length; i++)
          _VisitTimelineRow(
            entry: entries[i],
            isFirst: i == 0,
            isLast: i == entries.length - 1,
          ),
      ],
    );
  }
}

class _VisitTimelineRow extends StatelessWidget {
  const _VisitTimelineRow({
    required this.entry,
    required this.isFirst,
    required this.isLast,
  });

  final AssenVisitHistoryEntry entry;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenTimelineItem(
      date: entry.dateLabel,
      title: entry.title,
      isFirst: isFirst,
      isLast: isLast,
      accent: entry.isFirstVisit ? colors.brassMain : colors.roseMain,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (entry.isFirstVisit) ...[
            const AssenBadge(label: '첫 방문', hue: AssenBadgeHue.lemon),
            const SizedBox(width: SpacingTokens.s2),
          ],
          Text(
            entry.trailingLabel,
            style: TypographyTokens.label.copyWith(
              color: entry.kind == AssenVisitHistoryEntryKind.point
                  ? colors.matchaInk
                  : colors.ink700,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
