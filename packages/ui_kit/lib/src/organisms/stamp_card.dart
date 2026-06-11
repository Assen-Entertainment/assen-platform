import 'dart:math' as math;

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/card.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3).
const double _stampCounterSize = 13; // tokens.md §3 label — progress counter
const double _stampNumberSize = 11; // tokens.md §3 pixel — slot number

/// A stamp board (`8칸 (채움/빈칸/리워드)` — a signature motif).
///
/// Covers the Domain/StampCard row of `components.md` and the home hero
/// (screens.md C0). Implements the stamp-card motif from tokens.md §5: a grid
/// of [slots] (default 8, the 7–10 optimal band), where filled cells stamp with
/// double border and a slight rotation (−3..3°), empty cells are dashed rings,
/// and the final cell is the differentiated reward slot. A counter reads
/// "채운 수 / 전체". It composes onto an [AssenCard]; the stamp ink is the
/// strawberry hue (the key motif colour, ≤3 motif colours — tokens.md §6).
class AssenStampCard extends StatelessWidget {
  /// Creates a stamp board with [filled] of [slots] cells stamped.
  ///
  /// [title] labels the board (e.g. "방문 스탬프"). [rewardLabel] captions the
  /// final reward slot (e.g. "체키"). [filled] is clamped to `[0, slots]`.
  const AssenStampCard({
    required this.title,
    required this.filled,
    this.slots = 8,
    this.rewardLabel = '리워드',
    super.key,
  }) : assert(slots >= 1, 'A stamp board needs at least one slot');

  /// The board title.
  final String title;

  /// Total stamp slots (default 8 — the optimal 7–10 band, tokens.md §5).
  final int slots;

  /// Number of stamped (filled) cells; clamped to `[0, slots]`.
  final int filled;

  /// Caption for the final reward slot.
  final String rewardLabel;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final stamped = filled.clamp(0, slots);

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: _stampCounterSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              Text(
                '$stamped / $slots',
                style: TextStyle(
                  fontSize: _stampCounterSize,
                  fontWeight: FontWeight.w700,
                  color: colors.strawberryInk,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s4),
          // 4-per-row grid keeps an 8-slot board to two rows (tokens.md §5).
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: EdgeInsets.zero,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 4,
              mainAxisSpacing: SpacingTokens.s3,
              crossAxisSpacing: SpacingTokens.s3,
            ),
            itemCount: slots,
            itemBuilder: (context, index) {
              final isReward = index == slots - 1;
              final isStamped = index < stamped;
              return _StampSlot(
                number: index + 1,
                isStamped: isStamped,
                isReward: isReward,
                rewardLabel: rewardLabel,
                colors: colors,
              );
            },
          ),
        ],
      ),
    );
  }
}

/// A single stamp cell: dashed-ring empty, double-border stamped, reward final.
class _StampSlot extends StatelessWidget {
  const _StampSlot({
    required this.number,
    required this.isStamped,
    required this.isReward,
    required this.rewardLabel,
    required this.colors,
  });

  final int number;
  final bool isStamped;
  final bool isReward;
  final String rewardLabel;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    // Slight, deterministic rotation per stamped cell (−3..3°) — the
    // hand-pressed feel from tokens.md §5, seeded by the slot number so it
    // never jitters.
    final angle = isStamped ? ((number * 37) % 7 - 3) * math.pi / 180 : 0.0;
    final semanticLabel = isReward
        ? '$rewardLabel 보상 칸${isStamped ? ', 획득' : ''}'
        : '$number번 스탬프${isStamped ? ', 완료' : ', 비어 있음'}';

    final Widget face;
    if (isStamped) {
      face = Container(
        decoration: BoxDecoration(
          color: isReward ? colors.strawberryBg : colors.strawberryBgSubtle,
          shape: BoxShape.circle,
          border: Border.all(color: colors.strawberryBorder, width: 2),
        ),
        alignment: Alignment.center,
        child: Icon(
          isReward ? Icons.redeem : Icons.favorite,
          size: SpacingTokens.s5,
          color: colors.strawberryInk,
        ),
      );
    } else {
      // Empty cell — a dashed ring; the reward slot still names its prize.
      face = CustomPaint(
        painter: _DashedRingPainter(
          color: isReward ? colors.strawberryBorder : colors.ink300,
        ),
        child: Center(
          child: Text(
            isReward ? rewardLabel : '$number',
            style: TextStyle(
              fontSize: _stampNumberSize,
              fontWeight: FontWeight.w700,
              color: isReward ? colors.strawberryInk : colors.ink300,
            ),
          ),
        ),
      );
    }

    return Semantics(
      label: semanticLabel,
      child: Transform.rotate(
        angle: angle,
        child: AspectRatio(aspectRatio: 1, child: face),
      ),
    );
  }
}

/// Paints a dashed circular ring for an empty stamp slot.
class _DashedRingPainter extends CustomPainter {
  _DashedRingPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final center = size.center(Offset.zero);
    final radius = size.shortestSide / 2 - paint.strokeWidth;
    const dashCount = 24;
    const sweep = (2 * math.pi) / dashCount;
    for (var i = 0; i < dashCount; i += 2) {
      final start = i * sweep;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        start,
        sweep,
        false,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_DashedRingPainter oldDelegate) =>
      oldDelegate.color != color;
}
