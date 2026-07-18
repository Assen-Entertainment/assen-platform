import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A one-shot entry reveal: a soft fade + upward slide, optionally staggered by
/// [index]. The mobile counterpart of the web R13 `Reveal`/`Stagger` motion.
///
/// Motion is a brand signature, but it is strictly opt-out: when the platform
/// reports reduced motion (`MediaQuery.disableAnimations`, e.g. iOS "Reduce
/// Motion", or `accessibleNavigation`) this renders [child] immediately with no
/// animation at all (WCAG 2.3.3). It drives a single [TweenAnimationBuilder]
/// (no Timer, no repeating controller), so it settles deterministically under
/// `pumpAndSettle` and never leaves a pending timer in tests.
///
/// The stagger is baked into the animation curve via an [Interval] keyed on
/// [index] rather than a delayed start, so a list of reveals cascades in
/// without any of them scheduling their own clock.
class AssenReveal extends StatelessWidget {
  /// Wraps [child] in an entry reveal. [index] cascades a list (0 = first).
  const AssenReveal({
    required this.child,
    this.index = 0,
    this.offset = 12,
    super.key,
  });

  /// The content to reveal.
  final Widget child;

  /// Position in a cascading group; later items reveal slightly later.
  final int index;

  /// The upward slide distance (logical px) the child travels while fading in.
  final double offset;

  /// Total timeline for the cascade (the last item finishes by here).
  static const Duration _duration = MotionDurations.long;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.maybeOf(context);
    final reduceMotion =
        media != null &&
        (media.disableAnimations || media.accessibleNavigation);
    if (reduceMotion) return child;

    // Each item holds at t=0 until its slice of the timeline, then eases in.
    final start = (index * 0.09).clamp(0.0, 0.6);
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: _duration,
      curve: Interval(start, 1, curve: Curves.easeOutCubic),
      builder: (context, t, child) {
        final clamped = t.clamp(0.0, 1.0);
        return Opacity(
          opacity: clamped,
          child: Transform.translate(
            offset: Offset(0, (1 - clamped) * offset),
            child: child,
          ),
        );
      },
      child: child,
    );
  }
}
