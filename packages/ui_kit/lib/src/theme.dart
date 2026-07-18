import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Builds the Assen Platform light theme.
///
/// The colour scheme is the hand-mapped [AssenColorScheme] (composed from the
/// generated token ramp, NOT seeded — a seeded M3 scheme distorts the surface
/// tone). The raw token ramp is also exposed through the [AssenColors],
/// [AssenSpacing] and [AssenRadius] [ThemeExtension]s so the atoms read the
/// indigo/ink/container values that have no M3 `ColorScheme` slot.
class AssenTheme {
  const AssenTheme._();

  /// Primary CTA colour — the single solid action colour
  /// (color.ref.indigo.500, Assen Indigo). Not a seed: the scheme is
  /// hand-mapped, not [ColorScheme.fromSeed].
  static const Color primary = RefColors.indigo500;

  /// Returns the light [ThemeData] used by every Assen app.
  ///
  /// The token [ThemeExtension]s are registered here so every widget can read
  /// the full decorative ramp via `Theme.of(context).extension<AssenColors>()`
  /// (the atoms depend on this — the M3 [ColorScheme] alone cannot express the
  /// six pastel hues).
  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: AssenColorScheme.light,
      // Warm-paper canvas (mirrors web `--canvas`) so the white design-system
      // cards float with an editorial rhythm instead of blending into a pure
      // white background. Cards, app bar and bottom nav stay white/neutral.
      scaffoldBackgroundColor: AssenSurfaces.paper,
      extensions: const [AssenColors(), AssenSpacing(), AssenRadius()],
    );
  }

  /// Returns the dark [ThemeData] used by every Assen app.
  ///
  /// Mirrors [light]: the M3 [ColorScheme] is [AssenColorScheme.dark]
  /// (hand-mapped, not seeded) and `scaffoldBackgroundColor` is
  /// [AssenSurfaces.paperDark] — one step deeper than the scheme's `surface`
  /// so cards read as lifted off the canvas, the same depth relationship
  /// [light] gives the light theme (tokens.md §2/§3).
  ///
  /// The [AssenColors] extension is overridden field-by-field with the
  /// generated dark ramp (`docs/design/tokens.v2.json` `color.sysDark` /
  /// `color.ref.dark`, also mirrored to web `tokens.css` `.dark`). This is
  /// the load-bearing part: every ui_kit atom/molecule/organism reads colour
  /// through this extension (`colors.white`, `colors.ink900`, ...) rather
  /// than `Theme.of(context).colorScheme` directly, so remapping it here is
  /// what actually makes the component layer render correctly in dark mode.
  /// `indigo500`/`indigo600`/`indigoHover` and the decorative pastel pairs
  /// (lavender/violet/sky/pink/zinc) are left at their generated (light)
  /// defaults — they are self-contained fill+text pairs that stay AA-valid
  /// regardless of scaffold brightness, matching the web dark ramp, which
  /// leaves the same set unmirrored in `tokens.css` `.dark`.
  static ThemeData dark() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: AssenColorScheme.dark,
      scaffoldBackgroundColor: AssenSurfaces.paperDark,
      extensions: const [
        AssenColors(
          // "white" is the de facto card/sheet/app-bar-fill token consumed
          // across ui_kit (AssenCard, AssenDialog, AssenBottomSheet, ...) —
          // remapping it is what lifts cards off the dark canvas.
          white: RefColors.darkBg,
          neutral50: RefColors.darkSurface,
          neutral100: RefColors.darkSurfaceHigh,
          neutral200: RefColors.darkBorder,
          // Neutral200/300 collapse toward the same border tier as the light
          // ramp's own step is inverted for the dark palette; neutral300
          // reuses darkInkSub (not darkBorder) so it stays visually distinct
          // from neutral200 — e.g. AssenSkeleton lerps between the two for
          // its shimmer sweep, which would otherwise animate between two
          // identical colours and read as frozen.
          neutral300: RefColors.darkInkSub,
          // No distinct dark "hint" tier is specified upstream and ink400 has
          // no ui_kit consumer today; aliased to the secondary-text tier for
          // ramp consistency rather than left at its light value.
          ink400: RefColors.darkInkSub,
          ink500: RefColors.darkInkSub,
          // The web dark ramp has a single secondary-text tier
          // (`--on-surface-variant`); ink600 collapses onto it rather than
          // inventing an unvetted intermediate tone between ink500 and ink900.
          ink600: RefColors.darkInkSub,
          ink900: RefColors.darkInk,
          // Secondary-button/selected-chip container + its text, mirroring
          // `color.sysDark.primaryContainer`/`onPrimaryContainer`.
          indigo100: RefColors.indigoDarkContainer,
          indigoInk: RefColors.indigoOnDarkContainer,
          // Foreground-only indigo (text/icons painted directly on the dark
          // canvas/surface) lifted to the AA-safe tone — the base brand indigo
          // (indigo500, left unchanged above for button/icon FILLS) measures
          // only ≈3.42:1 on the dark canvas / ≈2.69:1 on surfaceContainerHigh,
          // both sub-AA for text (4.5:1 floor). See
          // [AssenColorScheme.indigoTextDark].
          indigoText: AssenColorScheme.indigoTextDark,
          greenMain: Color(0xFF3DD17E),
          amberMain: Color(0xFFF5B53D),
          mintBg: Color(0xFF14301F),
          mintInk: Color(0xFF6EE7A8),
          creamBg: Color(0xFF3A2E12),
          creamInk: Color(0xFFF5D98A),
          redMain: Color(0xFFFF6B6B),
          redBg: Color(0xFF3A1518),
          redInk: Color(0xFFFFB4B4),
        ),
        AssenSpacing(),
        AssenRadius(),
      ],
    );
  }
}
