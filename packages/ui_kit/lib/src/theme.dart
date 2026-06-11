import 'package:flutter/material.dart';

/// Builds the Assen Platform light theme.
///
/// Placeholder for P0: it only seeds Material 3 from the primary CTA colour
/// (`color.ref.rose.main` in docs/design/tokens.json). ASS-88 expands this into
/// the full semantic colour scheme, typography, and component themes.
class AssenTheme {
  const AssenTheme._();

  /// Primary CTA colour — the single solid action colour in the design system.
  static const Color primarySeed = Color(0xFFC2486B);

  /// Returns the light [ThemeData] used by every Assen app.
  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: primarySeed),
    );
  }
}
