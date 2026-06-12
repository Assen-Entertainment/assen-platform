import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/card.dart';

/// Direction of a [AssenStatCard] delta (drives the trend colour/arrow).
enum AssenStatTrend {
  /// No change shown.
  none,

  /// An increase (matcha — the success hue).
  up,

  /// A decrease (red).
  down,
}

/// An operator dashboard metric card (`운영자 지표`).
///
/// Covers the Domain/StatCard row of `components.md` — the operator dashboard's
/// daily figures. It is an [AssenCard] (level0 outline) holding a large [value]
/// over its [label], with an optional [delta] trend line. The value uses the
/// display face; the trend reads from both an arrow and its hue (matcha up /
/// red down), never colour alone (tokens.md §1). Plain numbers only — public
/// rankings are out of scope (operator-internal metrics, components.md).
class AssenStatCard extends StatelessWidget {
  /// Creates a metric card showing [value] labelled [label].
  ///
  /// [delta] is an optional change caption (e.g. "+12%"); [trend] colours and
  /// points its arrow. [icon] is an optional leading glyph for the metric.
  const AssenStatCard({
    required this.value,
    required this.label,
    this.delta,
    this.trend = AssenStatTrend.none,
    this.icon,
    super.key,
  });

  /// The metric value, pre-formatted (e.g. "1,284").
  final String value;

  /// The metric name (e.g. "오늘 방문").
  final String label;

  /// Optional change caption shown under the value.
  final String? delta;

  /// Trend direction for [delta] — see [AssenStatTrend].
  final AssenStatTrend trend;

  /// Optional leading glyph next to the label.
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Icon(icon, size: SpacingTokens.s4, color: colors.ink500),
                const SizedBox(width: SpacingTokens.s1),
              ],
              Flexible(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: TypographyTokens.labelSize,
                    fontWeight: FontWeight.w600,
                    color: colors.ink700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            value,
            style: TextStyle(
              fontSize: TypographyTokens.displayMSize,
              fontWeight: FontWeight.w800,
              color: colors.ink900,
            ),
          ),
          if (delta != null) ...[
            const SizedBox(height: SpacingTokens.s1),
            _Delta(delta: delta!, trend: trend, colors: colors),
          ],
        ],
      ),
    );
  }
}

/// The trend caption: an arrow + delta in the trend hue.
class _Delta extends StatelessWidget {
  const _Delta({
    required this.delta,
    required this.trend,
    required this.colors,
  });

  final String delta;
  final AssenStatTrend trend;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (trend) {
      AssenStatTrend.up => (colors.matchaInk, Icons.arrow_upward),
      AssenStatTrend.down => (colors.redMain, Icons.arrow_downward),
      AssenStatTrend.none => (colors.ink500, null),
    };

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[
          Icon(icon, size: SpacingTokens.s3, color: color),
          const SizedBox(width: SpacingTokens.s1),
        ],
        Text(
          delta,
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ],
    );
  }
}
