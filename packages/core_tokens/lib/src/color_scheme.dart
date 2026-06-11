// HAND-WRITTEN — NOT code-generated. See ADR-0004 + docs/design/tokens.md.
//
// WHY this file is excluded from codegen (#32 boundary):
//   The semantic Material 3 ColorScheme maps color.sys.* roles to the cream
//   palette. It is authored by hand on purpose: `ColorScheme.fromSeed` derives
//   a tonal palette that washes the cream surface toward grey/violet, which
//   violates the "크림 보정" principle (tokens.md §3) and the "surfaceTint off"
//   rule (§7). So the codegen pipeline emits only the raw ref ramp; this scheme
//   is composed from those generated primitives instead of being regenerated.
//   Editing THIS file by hand is expected — it has no generated header.

import 'package:core_tokens/src/colors.gen.dart';
import 'package:flutter/material.dart';

/// The Assen Platform light [ColorScheme], mapping color.sys.* roles to the
/// generated [RefColors] ramp.
///
/// Light mode only (the design system is light-first; a dark ramp can extend
/// [RefColors] later — tokens.md §2). Built from generated primitives so the
/// values never drift from `docs/design/tokens.json`.
abstract final class AssenColorScheme {
  /// The Assen Platform light scheme.
  ///
  /// `primary` is the single solid action colour (color.ref.rose.main).
  /// `surfaceTint` is pinned to `surface` (not primary) to disable the M3 tint
  /// overlay that would distort the cream surface (tokens.md §7).
  static const ColorScheme light = ColorScheme(
    brightness: Brightness.light,
    primary: RefColors.roseMain,
    onPrimary: RefColors.white,
    primaryContainer: RefColors.strawberryBg,
    onPrimaryContainer: RefColors.strawberryInk,
    secondary: RefColors.brassInk,
    onSecondary: RefColors.white,
    secondaryContainer: RefColors.brassBg,
    onSecondaryContainer: RefColors.brassInk,
    tertiary: RefColors.skyInk,
    onTertiary: RefColors.white,
    tertiaryContainer: RefColors.skyBg,
    onTertiaryContainer: RefColors.skyInk,
    error: RefColors.redMain,
    onError: RefColors.white,
    errorContainer: RefColors.redBg,
    onErrorContainer: RefColors.redInk,
    surface: RefColors.cream50,
    onSurface: RefColors.ink900,
    surfaceContainer: RefColors.white,
    surfaceContainerHigh: RefColors.cream100,
    onSurfaceVariant: RefColors.ink700,
    outline: RefColors.ink200,
    outlineVariant: RefColors.ink100,
    surfaceTint: RefColors.cream50,
  );
}
