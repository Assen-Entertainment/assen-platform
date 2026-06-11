import 'dart:math' as math;

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A linear progress bar (스탬프·목표 진행).
///
/// Covers the Feedback/ProgressBar row of `components.md`. The track is a
/// subtle pastel rail and the fill is the solid rose anchor; progress is a
/// 0–1 fraction so callers express "n of m" by dividing. Rounded ends keep it
/// soft. Solid fill, no gradient.
class AssenProgressBar extends StatelessWidget {
  /// Creates a progress bar filled to [value] (clamped to 0..1).
  const AssenProgressBar({required this.value, this.height = 8, super.key});

  /// Completion fraction in the range 0..1 (values outside are clamped).
  final double value;

  /// Bar thickness in logical pixels. Defaults to 8.
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final clamped = value.clamp(0.0, 1.0);

    return ClipRRect(
      borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.full)),
      child: LinearProgressIndicator(
        value: clamped,
        minHeight: height,
        backgroundColor: colors.strawberryBgSubtle,
        valueColor: AlwaysStoppedAnimation<Color>(colors.roseMain),
      ),
    );
  }
}

/// A circular progress ring (방문 진행 — the 회원증 3종 세트 motif).
///
/// Covers the Feedback/ProgressDonut row of `components.md`. Drawn with a
/// [CustomPainter] as a ring (an explicit inner radius, not a filled pie) so it
/// reads as the Japanese membership "donut" rather than a clock. The remaining
/// arc is a subtle pastel track; the completed arc is the solid rose anchor.
/// An optional [center] widget (e.g. "3/8") sits in the hole.
class AssenProgressDonut extends StatelessWidget {
  /// Creates a donut filled to [value] (clamped to 0..1).
  ///
  /// [size] is the outer diameter; [strokeWidth] sets the ring thickness (the
  /// inner radius is derived from it). [center] optionally fills the hole.
  const AssenProgressDonut({
    required this.value,
    this.size = 96,
    this.strokeWidth = 10,
    this.center,
    super.key,
  });

  /// Completion fraction in the range 0..1 (values outside are clamped).
  final double value;

  /// Outer diameter in logical pixels.
  final double size;

  /// Ring thickness in logical pixels (defines the inner radius).
  final double strokeWidth;

  /// Optional widget rendered in the centre hole (e.g. a count).
  final Widget? center;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _DonutPainter(
          value: value.clamp(0.0, 1.0),
          strokeWidth: strokeWidth,
          track: colors.strawberryBgSubtle,
          progress: colors.roseMain,
        ),
        child: center == null ? null : Center(child: center),
      ),
    );
  }
}

/// Paints the [AssenProgressDonut] ring (track + progress arc).
class _DonutPainter extends CustomPainter {
  const _DonutPainter({
    required this.value,
    required this.strokeWidth,
    required this.track,
    required this.progress,
  });

  final double value;
  final double strokeWidth;
  final Color track;
  final Color progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.shortestSide - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final trackPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = track;
    canvas.drawCircle(center, radius, trackPaint);

    if (value <= 0) return;
    final progressPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = progress;
    const start = -math.pi / 2; // 12 o'clock
    final sweep = 2 * math.pi * value;
    canvas.drawArc(rect, start, sweep, false, progressPaint);
  }

  @override
  bool shouldRepaint(_DonutPainter old) =>
      old.value != value ||
      old.strokeWidth != strokeWidth ||
      old.track != track ||
      old.progress != progress;
}

/// A carousel page indicator (dots).
///
/// Covers the Navigation/PageIndicator row of `components.md` — banner
/// carousels. The active dot is the solid rose anchor and slightly wider; the
/// rest are ink-ramp dots, so the current page reads by both size and colour.
class AssenPageIndicator extends StatelessWidget {
  /// Creates an indicator for [count] pages with [activeIndex] highlighted.
  const AssenPageIndicator({
    required this.count,
    required this.activeIndex,
    super.key,
  });

  /// Total number of pages.
  final int count;

  /// Zero-based index of the active page.
  final int activeIndex;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(count, (i) {
        final active = i == activeIndex;
        return AnimatedContainer(
          duration: MotionDurations.short,
          margin: const EdgeInsets.symmetric(horizontal: SpacingTokens.s1),
          width: active ? SpacingTokens.s4 : SpacingTokens.s2,
          height: SpacingTokens.s2,
          decoration: BoxDecoration(
            color: active ? colors.roseMain : colors.ink200,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.full),
            ),
          ),
        );
      }),
    );
  }
}
