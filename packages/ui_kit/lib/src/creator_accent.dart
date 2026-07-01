import 'dart:math' as math;

import 'package:flutter/painting.dart';

/// Runtime derivation of a creator's accent theme from a single base colour.
///
/// Design tokens cannot encode this: a creator picks an arbitrary `themeColor`
/// at runtime (see `docs/design/tokens.v2.json` → `creatorAccent`), so the
/// foreground / container roles must be derived live with a WCAG contrast
/// guarantee. The static brand defaults (`gradient.brand`, `color.sys.primary`
/// = Assen Indigo) remain in force; this only applies when a creator has set
/// `creator.themeColor != null` and only on the *accent surfaces* (profile
/// cover, follow/subscribe CTA, active tab, tier highlight) — global chrome
/// (BottomNav etc.) stays indigo.
///
/// Mirrors the Figma demonstration (CreatorProfile-ThemeA/B, `creator/accent`
/// variable with Teal/Coral modes). Source of `base`: the creator's chosen
/// colour, NOT a per-category value.
///
/// Roles produced:
///  * [accent]            — the creator's colour, used as a fill.
///  * [onAccent]          — black/white, whichever is more legible on [accent].
///  * [accentContainer]   — [accent] at 12% over the surface (subtle tint fill).
///  * [onAccentContainer] — [accent] darkened/lightened to meet AA on the tint.
@immutable
class CreatorAccent {
  const CreatorAccent({
    required this.accent,
    required this.onAccent,
    required this.accentContainer,
    required this.onAccentContainer,
  });

  final Color accent;
  final Color onAccent;
  final Color accentContainer;
  final Color onAccentContainer;

  /// WCAG 2.1 minimum contrast for normal-size text.
  static const double aaText = 4.5;

  /// WCAG 2.1 minimum contrast for UI components / large text.
  static const double aaUi = 3.0;

  /// Derive the full accent set from a creator-chosen [base] on [surface]
  /// (defaults to the app's white light surface; pass the dark base on dark
  /// mode so the 12% container tint blends against the right ground).
  factory CreatorAccent.fromBase(
    Color base, {
    Color surface = const Color(0xFFFFFFFF),
  }) {
    // An accent used as a *fill* keeps the creator's hue; we only nudge it when
    // it is so light it fails AA as a UI element on the surface (e.g. pale
    // yellow on white) so borders / thin accents stay visible. This is the
    // "미달색 → 보정" rule from the token note.
    final Color safeAccent = ensureContrast(base, surface, aaUi);
    final Color container = Color.lerp(surface, safeAccent, 0.12)!;
    return CreatorAccent(
      accent: safeAccent,
      onAccent: _bestForeground(safeAccent),
      accentContainer: container,
      onAccentContainer: ensureContrast(safeAccent, container, aaText),
    );
  }

  /// WCAG 2.1 relative-luminance contrast ratio between [a] and [b] (1..21).
  static double contrastRatio(Color a, Color b) {
    final double la = a.computeLuminance();
    final double lb = b.computeLuminance();
    final double hi = math.max(la, lb);
    final double lo = math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
  }

  /// Black or white — whichever is more legible on [bg].
  static Color _bestForeground(Color bg) {
    const Color white = Color(0xFFFFFFFF);
    const Color black = Color(0xFF000000);
    return contrastRatio(bg, white) >= contrastRatio(bg, black) ? white : black;
  }

  /// Shift [fg]'s lightness (toward black on a light [bg], toward white on a
  /// dark one) until it meets [target] contrast on [bg]. Hue and saturation are
  /// preserved so the creator's identity survives the correction. Returns the
  /// closest achievable colour if [target] cannot be reached.
  static Color ensureContrast(Color fg, Color bg, double target) {
    if (contrastRatio(fg, bg) >= target) return fg;
    final HSLColor hsl = HSLColor.fromColor(fg);
    final bool darken = bg.computeLuminance() > 0.5;
    Color best = fg;
    double bestRatio = contrastRatio(fg, bg);
    for (int i = 1; i <= 20; i++) {
      final double l = darken
          ? math.max(0.0, hsl.lightness - i * 0.05)
          : math.min(1.0, hsl.lightness + i * 0.05);
      final Color c = hsl.withLightness(l).toColor();
      final double r = contrastRatio(c, bg);
      if (r > bestRatio) {
        best = c;
        bestRatio = r;
      }
      if (r >= target) return c;
    }
    return best;
  }
}
