/// Material 3 window size classes used by Assen adaptive shells.
///
/// P0 intentionally collapses large and extra-large desktop widths into
/// [expanded]; the product need is chrome relocation and a readable content
/// column, not a separate desktop information architecture.
enum AssenWindowSize {
  /// Widths below 600dp keep the mobile bottom navigation pattern.
  compact,

  /// Widths from 600dp to 839dp use a collapsed navigation rail.
  medium,

  /// Widths at 840dp and above use an extended rail and centered body column.
  expanded;

  /// Maps logical width to the M3 compact/medium/expanded buckets.
  ///
  /// Boundary values are inclusive on the larger class: 600dp is [medium], and
  /// 840dp is [expanded]. This mirrors Material 3 window size classes while
  /// keeping P0 large/XL behaviour folded into [expanded].
  static AssenWindowSize fromWidth(double width) {
    if (width >= AssenLayout.expandedMinWidth) {
      return AssenWindowSize.expanded;
    }
    if (width >= AssenLayout.mediumMinWidth) {
      return AssenWindowSize.medium;
    }
    return AssenWindowSize.compact;
  }
}

/// Authored layout constants that are not generated design tokens.
///
/// These values describe responsive structure rather than visual styling:
/// Material 3 breakpoints and the maximum reading column for web/tablet. They
/// follow ADR-0004's token split: reusable colour/spacing/radius come from
/// `core_tokens`, while product layout thresholds live close to layout code.
abstract final class AssenLayout {
  /// The first Material 3 medium window class width in logical pixels.
  static const double mediumMinWidth = 600;

  /// The first Material 3 expanded window class width in logical pixels.
  static const double expandedMinWidth = 840;

  /// Maximum width for fan-app content on expanded web/tablet layouts.
  static const double contentMaxWidth = 1080;

  /// Maximum width for operator-console content on expanded layouts.
  ///
  /// Wider than [contentMaxWidth] because the console is a working surface
  /// (data lists, boards, tables) rather than a reading column, so it should
  /// use more of the available desktop width before centering.
  static const double consoleContentMaxWidth = 1440;
}
