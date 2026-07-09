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

/// The Assen Platform light and dark [ColorScheme]s, mapping color.sys.* /
/// color.sysDark.* roles to the generated [RefColors] ramp (Assen Indigo —
/// docs/design/tokens.v2.json).
///
/// Built from generated primitives so the values never drift from
/// `docs/design/tokens.v2.json`. [dark] transcribes `color.sysDark` by hand
/// (that JSON section is data only — ADR-0004 keeps ColorScheme composition
/// out of codegen), and is the same ramp mirrored into the web's
/// `tokens.css` `.dark` block.
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

  /// The Assen Platform dark scheme (`color.sysDark` —
  /// docs/design/tokens.v2.json, mirrored to web `tokens.css` `.dark`).
  ///
  /// `primary`/`onPrimary` stay [RefColors.indigo500]/[RefColors.white]
  /// unchanged — a filled-button/icon-on-fill colour, not a foreground painted
  /// directly on the dark canvas (see [indigoTextDark] for that case).
  /// `primaryContainer`/`onPrimaryContainer` step to the generated dark
  /// container pair ([RefColors.indigoDarkContainer] /
  /// [RefColors.indigoOnDarkContainer]). `surface` → `surfaceContainer` →
  /// `surfaceContainerHigh` step up through [RefColors.darkBg] →
  /// [RefColors.darkSurface] → [RefColors.darkSurfaceHigh] so cards read as
  /// lifted off the (deeper) scaffold canvas — see `AssenSurfaces.paperDark`
  /// in brand.dart. `outline`/`outlineVariant` collapse onto the same
  /// [RefColors.darkBorder] value, matching the web dark ramp (which does the
  /// same). `error`/`errorContainer`/`onErrorContainer` are the
  /// `color.sysDark` literals directly — `red.main` measures only ≈3:1 on the
  /// dark canvas (AA fails for text), so dark error is lifted brighter, same
  /// rationale as [indigoTextDark]. `tertiary`/`secondary` roles have no
  /// ui_kit consumer today (nothing in this codebase reads
  /// `Theme.of(context).colorScheme.secondary`/`.tertiary` — components read
  /// the `AssenColors` extension instead) so they are filled in for M3
  /// completeness/fallback-widget correctness rather than pixel-audited.
  static const ColorScheme dark = ColorScheme(
    brightness: Brightness.dark,
    primary: RefColors.indigo500,
    onPrimary: RefColors.white,
    primaryContainer: RefColors.indigoDarkContainer,
    onPrimaryContainer: RefColors.indigoOnDarkContainer,
    secondary: RefColors.darkInkSub,
    onSecondary: RefColors.darkBg,
    secondaryContainer: RefColors.darkSurfaceHigh,
    onSecondaryContainer: RefColors.darkInk,
    tertiary: RefColors.skyInk,
    onTertiary: RefColors.white,
    tertiaryContainer: RefColors.skyBg,
    onTertiaryContainer: RefColors.skyInk,
    error: Color(0xFFFF6B6B),
    onError: RefColors.white,
    errorContainer: Color(0xFF3A1518),
    onErrorContainer: Color(0xFFFFB4B4),
    surface: RefColors.darkBg,
    onSurface: RefColors.darkInk,
    surfaceContainer: RefColors.darkSurface,
    surfaceContainerHigh: RefColors.darkSurfaceHigh,
    onSurfaceVariant: RefColors.darkInkSub,
    outline: RefColors.darkBorder,
    outlineVariant: RefColors.darkBorder,
    surfaceTint: RefColors.darkBg,
  );

  /// Brand indigo lifted for dark-mode TEXT/ICON foregrounds painted directly
  /// on the dark canvas/surface — NOT a button fill (fills keep
  /// [RefColors.indigo500] unchanged, matching web `--primary` staying
  /// #5A4DF0 in `.dark`).
  ///
  /// Mirrors the web's hand-authored `--primary-bright`
  /// (`web/src/styles/globals.css` `.dark`, applied via `.dark .text-primary`):
  /// the base brand indigo measures only ≈3.42:1 as a foreground on the dark
  /// canvas (`surface`/scaffold — AA fails for body text, 4.5:1 floor) and
  /// only ≈2.69:1 on the lifted `surfaceContainerHigh` (cards/sheets — fails
  /// even harder). This lifted tone (same indigo family, lighter step —
  /// #A79BFF) clears ≈8.0:1 (AAA) on the dark canvas and stays comfortably
  /// above AA on `surfaceContainerHigh` too.
  ///
  /// Wired into ui_kit's `AssenColors.indigoText` semantic (see
  /// `ui_kit/lib/src/theme.dart` `AssenTheme.dark()`), which every
  /// foreground-on-indigo call site now reads instead of
  /// `AssenColors.indigo500` — the step indicator's current-step ring/number,
  /// the sidebar's selected nav label/icon, `AssenKeyValueRow`'s emphasised
  /// value, and `AssenAgreementCell`'s required-field tag. `indigo500` itself
  /// is untouched (button/icon FILLS stay #5A4DF0 in both themes).
  static const Color indigoTextDark = Color(0xFFA79BFF);
}
