import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A loading placeholder block with a gentle shimmer.
///
/// Covers the Feedback/Skeleton row of `components.md` (리스트형 / 카드형 — the
/// caller composes the shape by sizing/rounding). It pulses between two cream
/// steps using [MotionDurations] so the wait reads as "loading" rather than a
/// broken empty box. No gradient fills the block; the pulse animates a solid
/// colour. Honours `MediaQuery.disableAnimations` for reduced-motion users.
class AssenSkeleton extends StatefulWidget {
  /// Creates a skeleton block of [width]×[height] with corner [radius].
  ///
  /// For a circular avatar placeholder pass equal width/height and
  /// [radius] = half the size.
  const AssenSkeleton({
    this.width,
    this.height = 16,
    this.radius = RadiusTokens.sm,
    super.key,
  });

  /// Block width; null stretches to the parent's constraints.
  final double? width;

  /// Block height in logical pixels. Defaults to a text-line height.
  final double height;

  /// Corner radius in logical pixels.
  final double radius;

  @override
  State<AssenSkeleton> createState() => _AssenSkeletonState();
}

class _AssenSkeletonState extends State<AssenSkeleton>
    with SingleTickerProviderStateMixin {
  // Constructed eagerly in initState (not lazily) so dispose() can always tear
  // it down safely — a lazy controller would be built during dispose, which
  // triggers an unsafe ancestor lookup on a deactivated element.
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: MotionDurations.long,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;

    // Drive the controller from build so it follows the reduced-motion setting
    // even if it changes; repeat()/stop() are idempotent.
    if (reduceMotion) {
      _controller.stop();
      return DecoratedBox(
        decoration: BoxDecoration(
          color: colors.cream200,
          borderRadius: BorderRadius.all(Radius.circular(widget.radius)),
        ),
        child: SizedBox(width: widget.width, height: widget.height),
      );
    }
    if (!_controller.isAnimating) {
      _controller.repeat(reverse: true);
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_controller.value);
        return DecoratedBox(
          decoration: BoxDecoration(
            color: Color.lerp(colors.cream200, colors.cream300, t),
            borderRadius: BorderRadius.all(Radius.circular(widget.radius)),
          ),
          child: SizedBox(width: widget.width, height: widget.height),
        );
      },
    );
  }
}
