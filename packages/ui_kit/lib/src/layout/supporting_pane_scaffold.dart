import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/widgets.dart';
import 'package:ui_kit/src/layout/window_size.dart';

/// Material 3 "supporting pane" canonical layout.
///
/// A primary [main] pane takes the flexible remaining width while a
/// [supporting] pane sits beside it at a bounded width. Below [breakpoint] the
/// supporting pane stacks underneath the main pane (or is omitted), matching
/// M3's compact/medium collapse behaviour.
///
/// Widths are read from the LOCAL `constraints.maxWidth`, so this composes
/// correctly inside a desktop sidebar shell (the body, not the window, drives
/// the split). The supporting pane is clamped between [supportingMinWidth] and
/// [supportingMaxWidth] around [supportingFraction] of the available width, so
/// a narrow identity rail never balloons on an ultra-wide monitor.
///
/// Invariant: the smallest width admitted by [breakpoint] must exceed
/// `supportingMinWidth + gap`, otherwise the fixed-width supporting pane plus
/// the gap can overflow the row (the [Expanded] main pane can shrink to zero,
/// but the supporting [SizedBox] cannot). The defaults (breakpoint expanded =
/// 840dp, supportingMinWidth 280, gap from [SpacingTokens.s6]) satisfy this.
class AssenSupportingPaneScaffold extends StatelessWidget {
  /// Creates a supporting-pane layout.
  const AssenSupportingPaneScaffold({
    required this.main,
    required this.supporting,
    this.supportingPlacement = AssenSupportingPanePlacement.end,
    this.supportingFraction = 0.3,
    this.supportingMinWidth = 280,
    this.supportingMaxWidth = 400,
    this.gap = SpacingTokens.s6,
    this.breakpoint = AssenWindowSize.expanded,
    super.key,
  });

  /// The primary pane (flexible width).
  final Widget main;

  /// The secondary pane (bounded width beside [main], or stacked below).
  final Widget supporting;

  /// Whether the supporting pane sits at the start or end (default end/right).
  final AssenSupportingPanePlacement supportingPlacement;

  /// Target fraction of the available width for the supporting pane.
  final double supportingFraction;

  /// Lower bound for the supporting pane width when side-by-side.
  final double supportingMinWidth;

  /// Upper bound for the supporting pane width when side-by-side.
  final double supportingMaxWidth;

  /// Gap between the two panes (or between the stacked sections).
  final double gap;

  /// The smallest size class at which the panes sit side by side.
  final AssenWindowSize breakpoint;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = AssenWindowSize.fromWidth(constraints.maxWidth);
        if (!size.atLeast(breakpoint)) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              main,
              SizedBox(height: gap),
              supporting,
            ],
          );
        }

        final supportingWidth = (constraints.maxWidth * supportingFraction)
            .clamp(supportingMinWidth, supportingMaxWidth);
        final supportingPane = SizedBox(
          width: supportingWidth,
          child: supporting,
        );

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: switch (supportingPlacement) {
            AssenSupportingPanePlacement.start => [
              supportingPane,
              SizedBox(width: gap),
              Expanded(child: main),
            ],
            AssenSupportingPanePlacement.end => [
              Expanded(child: main),
              SizedBox(width: gap),
              supportingPane,
            ],
          },
        );
      },
    );
  }
}

/// Which side the supporting pane sits on when side-by-side.
enum AssenSupportingPanePlacement {
  /// Supporting pane at the start (left in LTR).
  start,

  /// Supporting pane at the end (right in LTR).
  end,
}
