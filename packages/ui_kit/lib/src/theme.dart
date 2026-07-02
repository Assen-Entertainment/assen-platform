import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Builds the Assen Platform light theme.
///
/// The colour scheme is the hand-mapped [AssenColorScheme] (composed from the
/// generated token ramp, NOT seeded — a seeded M3 scheme distorts the cream
/// surface). The raw token ramp is also exposed through the [AssenColors],
/// [AssenSpacing] and [AssenRadius] [ThemeExtension]s so the ASS-88 atoms read
/// pastel/ink/brass values that have no M3 `ColorScheme` slot. ASS-88 expands
/// this into typography and component themes.
class AssenTheme {
  const AssenTheme._();

  /// Primary CTA colour — the single solid action colour
  /// (color.ref.rose.main). Not a seed: the scheme is hand-mapped, not
  /// [ColorScheme.fromSeed]. Retained for ASS-88 component theming.
  static const Color primary = RefColors.roseMain;

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
      scaffoldBackgroundColor: RefColors.cream50,
      extensions: const [AssenColors(), AssenSpacing(), AssenRadius()],
    );
  }
}
