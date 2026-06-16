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

/// Picks a grid column count for [width] from per-size-class counts.
///
/// Reuses the Material 3 window size classes so grids densify with width
/// instead of being capped at one fixed column count — e.g. the cheki album
/// shows more frames per row on web/tablet while keeping the mobile layout
/// unchanged. Callers pass the column count for each class explicitly so the
/// progression stays a deliberate design choice, not an emergent one.
int assenGridCrossAxisCount(
  double width, {
  required int compact,
  required int medium,
  required int expanded,
}) => switch (AssenWindowSize.fromWidth(width)) {
  AssenWindowSize.compact => compact,
  AssenWindowSize.medium => medium,
  AssenWindowSize.expanded => expanded,
};

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
  ///
  /// Sized so the expanded fan surfaces (notably the home dashboard) use more
  /// of a desktop browser's width before centering, instead of leaving wide
  /// empty gutters around a narrow reading column. The home screen lays its
  /// sections into two columns at this width; other fan screens read wider.
  static const double contentMaxWidth = 1280;

  /// Maximum width for a centered form body (login, signup) before it stops
  /// stretching edge-to-edge.
  ///
  /// Auth screens are fixed-height (non-scrolling) bodies, so they cannot use
  /// AssenContentColumn (which loosens height for scrolling content); the
  /// AssenFormFrame caps them to this width via symmetric padding instead.
  static const double formMaxWidth = 420;

  /// Maximum width for operator-console content on expanded layouts.
  ///
  /// Wider than [contentMaxWidth] because the console is a working surface
  /// (data lists, boards, tables) rather than a reading column, so it should
  /// use more of the available desktop width before centering.
  static const double consoleContentMaxWidth = 1440;
}
