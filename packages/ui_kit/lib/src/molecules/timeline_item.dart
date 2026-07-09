import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A single timeline entry with a connecting rail (`방문 / 포인트 내역`).
///
/// Covers the Content/TimelineItem row of `components.md` and is the base for
/// the VisitLogItem and PointHistoryCell variants (visit and point histories).
/// A node dot sits on a vertical rail; [isFirst]/[isLast] trim the rail so a
/// list of these reads as one continuous thread. The frame is visit- and
/// log-centric (references #12 — never a "기념일" countdown): [date] is the when,
/// [title] the what, [subtitle] the detail (e.g. "만난 캐스트: 미오").
///
/// [trailing] is a free slot for a value (e.g. a "+120 P" point delta or a
/// badge); [accent] tints the node dot for cast-coloured entries.
class AssenTimelineItem extends StatelessWidget {
  /// Creates a timeline entry.
  ///
  /// [isFirst]/[isLast] control rail trimming at the ends of a list. [trailing]
  /// is an optional trailing slot widget; [accent] optionally recolours the
  /// node dot (defaults to the indigo anchor).
  const AssenTimelineItem({
    required this.date,
    required this.title,
    this.subtitle,
    this.trailing,
    this.isFirst = false,
    this.isLast = false,
    this.accent,
    super.key,
  });

  /// The entry's date/time label (the "when").
  final String date;

  /// The entry's primary text (the "what").
  final String title;

  /// Optional detail line under the title.
  final String? subtitle;

  /// Optional trailing slot (a value, badge, …).
  final Widget? trailing;

  /// Whether this is the first entry (trims the rail above the node).
  final bool isFirst;

  /// Whether this is the last entry (trims the rail below the node).
  final bool isLast;

  /// Optional node-dot colour override (e.g. a cast identity colour). Defaults
  /// to the indigo action anchor.
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final dotColor = accent ?? colors.indigo500;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Rail(
            dotColor: dotColor,
            isFirst: isFirst,
            isLast: isLast,
            c: colors,
          ),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: SpacingTokens.s4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    date,
                    style: TextStyle(
                      fontSize: TypographyTokens.bodySSize,
                      color: colors.ink500,
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.s1),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: TextStyle(
                            fontSize: TypographyTokens.titleMSize,
                            fontWeight: FontWeight.w600,
                            color: colors.ink900,
                          ),
                        ),
                      ),
                      if (trailing != null) ...[
                        const SizedBox(width: SpacingTokens.s2),
                        trailing!,
                      ],
                    ],
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: SpacingTokens.s1),
                    Text(
                      subtitle!,
                      style: TextStyle(
                        fontSize: TypographyTokens.bodySSize,
                        color: colors.ink600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The vertical rail + node dot for one [AssenTimelineItem].
class _Rail extends StatelessWidget {
  const _Rail({
    required this.dotColor,
    required this.isFirst,
    required this.isLast,
    required this.c,
  });

  final Color dotColor;
  final bool isFirst;
  final bool isLast;
  final AssenColors c;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: SpacingTokens.s3,
      child: Column(
        children: [
          Expanded(
            child: Container(
              width: 2,
              color: isFirst ? Colors.transparent : c.neutral200,
            ),
          ),
          Container(
            width: SpacingTokens.s3,
            height: SpacingTokens.s3,
            decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
          ),
          Expanded(
            child: Container(
              width: 2,
              color: isLast ? Colors.transparent : c.neutral200,
            ),
          ),
        ],
      ),
    );
  }
}
