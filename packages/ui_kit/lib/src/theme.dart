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
}
