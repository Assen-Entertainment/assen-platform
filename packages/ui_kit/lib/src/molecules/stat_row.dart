import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// One value/label pair in an [AssenStatRow].
@immutable
class AssenStat {
  /// Creates a stat with a pre-formatted [value] and a [label].
  const AssenStat({required this.value, required this.label});

  /// The metric value, pre-formatted (e.g. `1,284`).
  final String value;

  /// The metric name shown under the value (e.g. `팔로워`).
  final String label;
}

/// A compact inline row of profile stats (value over label), evenly spaced.
///
/// The mobile counterpart of the web profile stat strip: unlike the operator
/// `AssenStatCard` (one big dashboard figure), this packs several small
/// value/label pairs — e.g. `팔로워 / 게시물` — in a single row divided by hairlines.
/// Domain-agnostic; every colour/spacing comes from the tokens.
class AssenStatRow extends StatelessWidget {
  /// Creates a stat row from [stats].
  ///
  /// An empty list renders an empty row; callers supply at least one stat.
  const AssenStatRow({required this.stats, super.key});

  /// The stats rendered left-to-right, separated by hairline dividers.
  final List<AssenStat> stats;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final children = <Widget>[];
    for (var i = 0; i < stats.length; i++) {
      if (i > 0) {
        children.add(
          Container(
            width: 1,
            height: SpacingTokens.s8,
            color: colors.ink100,
          ),
        );
      }
      children.add(
        Expanded(
          child: _StatCell(stat: stats[i], colors: colors),
        ),
      );
    }

    return Row(children: children);
  }
}

/// A single centred value-over-label cell.
class _StatCell extends StatelessWidget {
  const _StatCell({required this.stat, required this.colors});

  final AssenStat stat;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          stat.value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: TypographyTokens.titleLSize,
            fontWeight: FontWeight.w800,
            color: colors.ink900,
          ),
        ),
        const SizedBox(height: SpacingTokens.s1),
        Text(
          stat.label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            color: colors.ink500,
          ),
        ),
      ],
    );
  }
}
