/// Material 3 window size classes used by Assen adaptive shells.
///
/// The full M3 ladder compact → extraLarge. Mobile/tablet chrome (bottom bar →
/// collapsed rail → extended rail + centered reading column) lives at
/// compact/medium/expanded; the fan web desktop information architecture
/// (persistent sidebar + canonical layouts that fill the width) engages at
/// [large] and [extraLarge]. Call sites that mean "expanded and wider" use
/// [atLeast] so the legacy extended-rail/content-column path (operator console)
/// keeps working unchanged now that large/XL are no longer folded into
/// [expanded].
enum AssenWindowSize {
  /// Widths below 600dp keep the mobile bottom navigation pattern.
  compact,

  /// Widths from 600dp to 839dp use a collapsed navigation rail.
  medium,

  /// Widths from 840dp to 1199dp use an extended rail and centered column.
  expanded,

  /// Widths from 1200dp to 1599dp begin the desktop sidebar layout.
  large,

  /// Widths at 1600dp and above use the widest desktop sidebar layout.
  extraLarge;

  /// Maps logical width to the M3 size-class buckets.
  ///
  /// Boundary values are inclusive on the larger class: 600dp is [medium],
  /// 840dp is [expanded], 1200dp is [large], and 1600dp is [extraLarge].
  static AssenWindowSize fromWidth(double width) {
    if (width >= AssenLayout.extraLargeMinWidth) {
      return AssenWindowSize.extraLarge;
    }
    if (width >= AssenLayout.largeMinWidth) {
      return AssenWindowSize.large;
    }
    if (width >= AssenLayout.expandedMinWidth) {
      return AssenWindowSize.expanded;
    }
    if (width >= AssenLayout.mediumMinWidth) {
      return AssenWindowSize.medium;
    }
    return AssenWindowSize.compact;
  }

  /// Whether this class is at least as wide as [other], by class order.
  ///
  /// Lets "expanded and wider" call sites survive un-collapsing large/XL from
  /// [expanded]: `size.atLeast(AssenWindowSize.expanded)` stays true at [large]
  /// and [extraLarge], so the legacy rail + content-column path is preserved.
  bool atLeast(AssenWindowSize other) => index >= other.index;
}

/// Picks a grid column count for [width] from per-size-class counts.
///
/// Reuses the Material 3 window size classes so grids densify with width
/// instead of being capped at one fixed column count — e.g. the cheki album
/// shows more frames per row on web/tablet while keeping the mobile layout
/// unchanged. Callers pass the column count for each class explicitly so the
/// progression stays a deliberate design choice, not an emergent one.
/// Pass the width of the LOCAL grid/pane, not the raw window: a desktop sidebar
/// shrinks the body below the window width, so window-width math over-counts
/// columns. [large]/[extraLarge] are optional and fall back to [expanded] (then
/// [large]) so existing 3-arg callers compile unchanged.
int assenGridCrossAxisCount(
  double width, {
  required int compact,
  required int medium,
  required int expanded,
  int? large,
  int? extraLarge,
}) => switch (AssenWindowSize.fromWidth(width)) {
  AssenWindowSize.compact => compact,
  AssenWindowSize.medium => medium,
  AssenWindowSize.expanded => expanded,
  AssenWindowSize.large => large ?? expanded,
  AssenWindowSize.extraLarge => extraLarge ?? large ?? expanded,
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

  /// The first Material 3 large window class width in logical pixels.
  ///
  /// At and above this width the fan web shell switches from a navigation rail
  /// to a persistent desktop sidebar and surfaces lay out as canonical
  /// (feed / supporting-pane / list-detail) layouts rather than a centered
  /// reading column.
  static const double largeMinWidth = 1200;

  /// The first Material 3 extra-large window class width in logical pixels.
  static const double extraLargeMinWidth = 1600;

  /// Fixed width of the persistent desktop sidebar at [AssenWindowSize.large]
  /// and wider (non-collapsible in this version).
  static const double sidebarWidth = 256;

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
