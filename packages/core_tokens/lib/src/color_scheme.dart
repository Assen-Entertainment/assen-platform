// HAND-WRITTEN — NOT code-generated. See ADR-0004 + docs/design/tokens.md.
//
// WHY this file is excluded from codegen (#32 boundary):
//   The semantic Material 3 ColorScheme maps color.sys.* roles to the Assen
//   Indigo palette (docs/design/tokens.v2.json). It is authored by hand on
//   purpose: `ColorScheme.fromSeed` derives a tonal palette that washes the
//   clean white surface toward grey/violet, which violates the surface-tone
//   principle (tokens.md §3) and the "surfaceTint off" rule (§7). The codegen
//   pipeline emits only the raw ref ramp; this scheme is composed from those
//   generated primitives, not regenerated. Hand-editing THIS file is expected
//   — it has no generated header.

import 'package:core_tokens/src/colors.gen.dart';
import 'package:flutter/material.dart';

/// The Assen Platform light [ColorScheme], mapping color.sys.* roles to the
/// generated [RefColors] ramp (Assen Indigo — docs/design/tokens.v2.json).
///
/// Light mode only (the design system is light-first; a dark ramp can extend
/// [RefColors] later — tokens.md §2). Built from generated primitives so the
/// values never drift from `docs/design/tokens.v2.json`.
abstract final class AssenColorScheme {
  /// The Assen Platform light scheme.
  ///
  /// `primary` is the single solid action colour (color.ref.indigo.500 —
  /// Assen Indigo #5A4DF0). `surfaceTint` is pinned to `surface` (not primary)
  /// to disable the M3 tint overlay that would distort the surface (§7).
  static const ColorScheme light = ColorScheme(
    brightness: Brightness.light,
    primary: RefColors.indigo500,
    onPrimary: RefColors.white,
    primaryContainer: RefColors.indigo100,
    onPrimaryContainer: RefColors.indigoInk,
    secondary: RefColors.ink600,
    onSecondary: RefColors.white,
    secondaryContainer: RefColors.neutral100,
    onSecondaryContainer: RefColors.ink900,
    tertiary: RefColors.skyInk,
    onTertiary: RefColors.white,
    tertiaryContainer: RefColors.skyBg,
    onTertiaryContainer: RefColors.skyInk,
    error: RefColors.redMain,
    onError: RefColors.white,
    errorContainer: RefColors.redBg,
    onErrorContainer: RefColors.redInk,
    surface: RefColors.white,
    onSurface: RefColors.ink900,
    surfaceContainer: RefColors.white,
    surfaceContainerHigh: RefColors.neutral100,
    onSurfaceVariant: RefColors.ink500,
    outline: RefColors.neutral200,
    outlineVariant: RefColors.neutral100,
    surfaceTint: RefColors.white,
  );
}
