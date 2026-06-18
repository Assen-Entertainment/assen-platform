import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/molecules/timeline_item.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/empty_state.dart';

/// Summary copy for the fan-facing F3 points ledger.
///
/// ASS-142 keeps this read-only and point-denominated only, so approval-gated
/// coupon value or cash-equivalent copy never enters the template API.
class AssenPointsSummary {
  /// Creates the F3 summary shown above the monthly points timeline.
  const AssenPointsSummary({
    required this.balance,
    required this.expiryNote,
  });

  /// Current available point balance, displayed as a formatted `P` amount.
  final int balance;

  /// Fan-facing expiry note vetted by the app layer.
  final String expiryNote;
}

/// One row in the F3 points ledger.
///
/// The sign of [delta] is the only visual semantic: positive rows are accruals,
/// negative rows are usage. This avoids a second enum that could drift from the
/// ledger amount.
class AssenPointEntry {
  /// Creates a point ledger row for a monthly timeline section.
  const AssenPointEntry({
    required this.title,
    required this.dateLabel,
    required this.delta,
  });

  /// Primary ledger description.
  final String title;

  /// Korean date label rendered above the title.
  final String dateLabel;

  /// Signed point delta; positive accrues and negative spends points.
  final int delta;
}

/// A month section in reverse-chronological F3 points history.
class AssenPointsMonthGroup {
  /// Creates a month group with newest point entries first.
  const AssenPointsMonthGroup({
    required this.monthLabel,
    required this.entries,
  });

  /// Month label, e.g. `6월`.
  final String monthLabel;

  /// Point entries belonging to this month.
  final List<AssenPointEntry> entries;
}

/// Fan-facing points history screen template (F3).
///
/// ASS-142 mirrors the visit-history timeline structure while keeping all copy
/// point-only. The template owns layout, token usage, formatting, and the empty
/// state; callers own data filtering and approval-gated business meaning.
class AssenPointsHistoryTemplate extends StatelessWidget {
  /// Creates the points-history template.
  const AssenPointsHistoryTemplate({
    required this.summary,
    required this.monthGroups,
    this.onBack,
    super.key,
  });

  /// Current points summary shown in the header.
  final AssenPointsSummary summary;

  /// Month-grouped point rows, newest first.
  final List<AssenPointsMonthGroup> monthGroups;

  /// Optional back handler for nested fan-app routes.
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '포인트 내역', onBack: onBack),
      body: monthGroups.isEmpty
          ? const AssenEmptyState(
              title: '포인트 내역이 없어요',
              message: '적립하거나 사용한 포인트가 아직 없습니다.',
            )
          : CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: _PointsSummaryHeader(summary: summary),
                ),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(
                    SpacingTokens.screenMargin,
                    SpacingTokens.s5,
                    SpacingTokens.screenMargin,
                    SpacingTokens.s8,
                  ),
                  sliver: SliverList.list(
                    children: [
                      for (final group in monthGroups) ...[
                        AssenSectionHeader(title: group.monthLabel),
                        const SizedBox(height: SpacingTokens.s3),
                        _PointsTimeline(entries: group.entries),
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

/// The Scaffold-less points-history body for embedding in a list-detail pane
/// (ASS-147 Slice 4): the same summary header + monthly point timelines as
/// [AssenPointsHistoryTemplate] but WITHOUT a [Scaffold] or [AssenAppBar], so
/// it mounts as the detail pane of the My hub. The route-built full-Scaffold
/// template is unchanged.
class AssenPointsHistoryBody extends StatelessWidget {
  /// Creates an embeddable points-history body.
  const AssenPointsHistoryBody({
    required this.summary,
    required this.monthGroups,
    super.key,
  });

  /// Current points summary shown in the header.
  final AssenPointsSummary summary;

  /// Month-grouped point rows, newest first.
  final List<AssenPointsMonthGroup> monthGroups;

  @override
  Widget build(BuildContext context) {
    if (monthGroups.isEmpty) {
      return const AssenEmptyState(
        title: '포인트 내역이 없어요',
        message: '적립하거나 사용한 포인트가 아직 없습니다.',
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _PointsSummaryHeader(summary: summary),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s5,
            SpacingTokens.screenMargin,
            SpacingTokens.s8,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final group in monthGroups) ...[
                AssenSectionHeader(title: group.monthLabel),
                const SizedBox(height: SpacingTokens.s3),
                _PointsTimeline(entries: group.entries),
                const SizedBox(height: SpacingTokens.s5),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _PointsSummaryHeader extends StatelessWidget {
  const _PointsSummaryHeader({required this.summary});

  final AssenPointsSummary summary;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s5,
            SpacingTokens.screenMargin,
            SpacingTokens.s6,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '보유 포인트',
                style: TypographyTokens.captionMicro.copyWith(
                  color: colors.ink700,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                _formatPoints(summary.balance),
                style: TypographyTokens.displayL.copyWith(
                  color: colors.roseMain,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                summary.expiryNote,
                style: TypographyTokens.captionMicro.copyWith(
                  color: colors.ink500,
                ),
              ),
            ],
          ),
        ),
        Container(height: SpacingTokens.s2, color: colors.cream100),
      ],
    );
  }
}

class _PointsTimeline extends StatelessWidget {
  const _PointsTimeline({required this.entries});

  final List<AssenPointEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < entries.length; i++)
          _PointsTimelineRow(
            entry: entries[i],
            isFirst: i == 0,
            isLast: i == entries.length - 1,
          ),
      ],
    );
  }
}

class _PointsTimelineRow extends StatelessWidget {
  const _PointsTimelineRow({
    required this.entry,
    required this.isFirst,
    required this.isLast,
  });

  final AssenPointEntry entry;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isPositive = entry.delta >= 0;

    return AssenTimelineItem(
      date: entry.dateLabel,
      title: entry.title,
      isFirst: isFirst,
      isLast: isLast,
      accent: isPositive ? colors.roseMain : colors.ink500,
      trailing: Text(
        _formatDelta(entry.delta),
        style: TypographyTokens.label.copyWith(
          color: isPositive ? colors.roseMain : colors.ink900,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

String _formatPoints(int value) => '${_formatNumber(value)} P';

String _formatDelta(int value) {
  final sign = value >= 0 ? '+' : '−';
  return '$sign${_formatNumber(value.abs())} P';
}

String _formatNumber(int value) {
  final raw = value.toString();
  final buffer = StringBuffer();

  for (var i = 0; i < raw.length; i++) {
    final remaining = raw.length - i;
    buffer.write(raw[i]);
    if (remaining > 1 && remaining % 3 == 1) {
      buffer.write(',');
    }
  }

  return buffer.toString();
}
