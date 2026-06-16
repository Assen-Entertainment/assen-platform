import 'dart:math' as math;

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/widgets.dart';
import 'package:ui_kit/src/layout/window_size.dart';

/// Centers page content in an Assen expanded-width content column.
///
/// The wrapper is always a [Center] plus [ConstrainedBox]; below [maxWidth] it
/// naturally has no visible effect because the parent is already narrower than
/// the maximum. Keeping the same wrapper across widths avoids each screen
/// carrying its own web-specific constraint logic. [maxWidth] defaults to the
/// fan reading column ([AssenLayout.contentMaxWidth]); the operator console
/// passes the wider [AssenLayout.consoleContentMaxWidth].
class AssenContentColumn extends StatelessWidget {
  /// Creates a centered content column around [child].
  const AssenContentColumn({
    required this.child,
    this.maxWidth = AssenLayout.contentMaxWidth,
    super.key,
  });

  /// The page body constrained to [maxWidth].
  final Widget child;

  /// The maximum content width before the column centers in available space.
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}

/// Caps a fixed-height (non-scrolling) page body to a centered [maxWidth]
/// without loosening the incoming height constraints.
///
/// [AssenContentColumn] wraps content in a [Center], which suits scrolling
/// bodies — a [CustomScrollView] supplies its own viewport height — but loosens
/// the vertical axis and so breaks children that need bounded height, such as
/// [Expanded] or `MainAxisAlignment.center`. This frame caps only the
/// horizontal axis by widening symmetric padding, so fixed-height form bodies
/// (login, signup) stay vertically laid out while no longer stretching
/// edge-to-edge on web/desktop widths. Below [maxWidth] (plus margins) it
/// falls back to [minPadding] screen gutters. The child is expected to fill
/// the padded region (e.g. a stretch-aligned [Column]); a narrower child is
/// left-aligned within it rather than re-centered.
class AssenFormFrame extends StatelessWidget {
  /// Creates a width-capped frame around a fixed-height [child].
  const AssenFormFrame({
    required this.child,
    this.maxWidth = AssenLayout.formMaxWidth,
    this.minPadding = SpacingTokens.screenMargin,
    super.key,
  });

  /// The fixed-height page body, capped to [maxWidth] and centered.
  final Widget child;

  /// The maximum content width before the body centers in available space.
  final double maxWidth;

  /// The minimum horizontal gutter retained when the body is at full width.
  final double minPadding;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final available = constraints.maxWidth;
        final horizontal = available.isFinite
            ? math.max(minPadding, (available - maxWidth) / 2)
            : minPadding;
        return Padding(
          padding: EdgeInsets.symmetric(horizontal: horizontal),
          child: child,
        );
      },
    );
  }
}
