// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.v2.json (Assen Indigo — W3C DTCG 2025.10).
// Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).

import 'package:flutter/material.dart';

import 'colors.gen.dart';
import 'radius.gen.dart';
import 'spacing.gen.dart';

/// Raw reference colours exposed as a [ThemeExtension].
///
/// Read with `Theme.of(context).extension<AssenColors>()`. Defaults mirror
/// [RefColors]; a dark ramp can be added later by passing overrides. The
/// semantic ColorScheme is NOT here — it is hand-mapped in ui_kit.
final class AssenColors extends ThemeExtension<AssenColors> {
  const AssenColors({
    this.white = RefColors.white,
    this.neutral50 = RefColors.neutral50,
    this.neutral100 = RefColors.neutral100,
    this.neutral200 = RefColors.neutral200,
    this.neutral300 = RefColors.neutral300,
    this.ink400 = RefColors.ink400,
    this.ink500 = RefColors.ink500,
    this.ink600 = RefColors.ink600,
    this.ink900 = RefColors.ink900,
    this.darkBg = RefColors.darkBg,
    this.darkSurface = RefColors.darkSurface,
    this.darkSurfaceHigh = RefColors.darkSurfaceHigh,
    this.darkBorder = RefColors.darkBorder,
    this.darkInk = RefColors.darkInk,
    this.darkInkSub = RefColors.darkInkSub,
    this.indigo100 = RefColors.indigo100,
    this.indigo500 = RefColors.indigo500,
    this.indigo600 = RefColors.indigo600,
    this.indigoHover = RefColors.indigoHover,
    this.indigoInk = RefColors.indigoInk,
    this.indigoDarkContainer = RefColors.indigoDarkContainer,
    this.indigoOnDarkContainer = RefColors.indigoOnDarkContainer,
    this.lavenderBg = RefColors.lavenderBg,
    this.lavenderInk = RefColors.lavenderInk,
    this.violetBg = RefColors.violetBg,
    this.violetInk = RefColors.violetInk,
    this.creamBg = RefColors.creamBg,
    this.creamInk = RefColors.creamInk,
    this.mintBg = RefColors.mintBg,
    this.mintInk = RefColors.mintInk,
    this.skyBg = RefColors.skyBg,
    this.skyInk = RefColors.skyInk,
    this.pinkBg = RefColors.pinkBg,
    this.pinkInk = RefColors.pinkInk,
    this.zincBg = RefColors.zincBg,
    this.zincInk = RefColors.zincInk,
    this.greenMain = RefColors.greenMain,
    this.amberMain = RefColors.amberMain,
    this.redMain = RefColors.redMain,
    this.redBg = RefColors.redBg,
    this.redInk = RefColors.redInk,
  });

  final Color white;
  final Color neutral50;
  final Color neutral100;
  final Color neutral200;
  final Color neutral300;
  final Color ink400;
  final Color ink500;
  final Color ink600;
  final Color ink900;
  final Color darkBg;
  final Color darkSurface;
  final Color darkSurfaceHigh;
  final Color darkBorder;
  final Color darkInk;
  final Color darkInkSub;
  final Color indigo100;
  final Color indigo500;
  final Color indigo600;
  final Color indigoHover;
  final Color indigoInk;
  final Color indigoDarkContainer;
  final Color indigoOnDarkContainer;
  final Color lavenderBg;
  final Color lavenderInk;
  final Color violetBg;
  final Color violetInk;
  final Color creamBg;
  final Color creamInk;
  final Color mintBg;
  final Color mintInk;
  final Color skyBg;
  final Color skyInk;
  final Color pinkBg;
  final Color pinkInk;
  final Color zincBg;
  final Color zincInk;
  final Color greenMain;
  final Color amberMain;
  final Color redMain;
  final Color redBg;
  final Color redInk;

  @override
  AssenColors copyWith({
    Color? white,
    Color? neutral50,
    Color? neutral100,
    Color? neutral200,
    Color? neutral300,
    Color? ink400,
    Color? ink500,
    Color? ink600,
    Color? ink900,
    Color? darkBg,
    Color? darkSurface,
    Color? darkSurfaceHigh,
    Color? darkBorder,
    Color? darkInk,
    Color? darkInkSub,
    Color? indigo100,
    Color? indigo500,
    Color? indigo600,
    Color? indigoHover,
    Color? indigoInk,
    Color? indigoDarkContainer,
    Color? indigoOnDarkContainer,
    Color? lavenderBg,
    Color? lavenderInk,
    Color? violetBg,
    Color? violetInk,
    Color? creamBg,
    Color? creamInk,
    Color? mintBg,
    Color? mintInk,
    Color? skyBg,
    Color? skyInk,
    Color? pinkBg,
    Color? pinkInk,
    Color? zincBg,
    Color? zincInk,
    Color? greenMain,
    Color? amberMain,
    Color? redMain,
    Color? redBg,
    Color? redInk,
  }) {
    return AssenColors(
      white: white ?? this.white,
      neutral50: neutral50 ?? this.neutral50,
      neutral100: neutral100 ?? this.neutral100,
      neutral200: neutral200 ?? this.neutral200,
      neutral300: neutral300 ?? this.neutral300,
      ink400: ink400 ?? this.ink400,
      ink500: ink500 ?? this.ink500,
      ink600: ink600 ?? this.ink600,
      ink900: ink900 ?? this.ink900,
      darkBg: darkBg ?? this.darkBg,
      darkSurface: darkSurface ?? this.darkSurface,
      darkSurfaceHigh: darkSurfaceHigh ?? this.darkSurfaceHigh,
      darkBorder: darkBorder ?? this.darkBorder,
      darkInk: darkInk ?? this.darkInk,
      darkInkSub: darkInkSub ?? this.darkInkSub,
      indigo100: indigo100 ?? this.indigo100,
      indigo500: indigo500 ?? this.indigo500,
      indigo600: indigo600 ?? this.indigo600,
      indigoHover: indigoHover ?? this.indigoHover,
      indigoInk: indigoInk ?? this.indigoInk,
      indigoDarkContainer: indigoDarkContainer ?? this.indigoDarkContainer,
      indigoOnDarkContainer:
          indigoOnDarkContainer ?? this.indigoOnDarkContainer,
      lavenderBg: lavenderBg ?? this.lavenderBg,
      lavenderInk: lavenderInk ?? this.lavenderInk,
      violetBg: violetBg ?? this.violetBg,
      violetInk: violetInk ?? this.violetInk,
      creamBg: creamBg ?? this.creamBg,
      creamInk: creamInk ?? this.creamInk,
      mintBg: mintBg ?? this.mintBg,
      mintInk: mintInk ?? this.mintInk,
      skyBg: skyBg ?? this.skyBg,
      skyInk: skyInk ?? this.skyInk,
      pinkBg: pinkBg ?? this.pinkBg,
      pinkInk: pinkInk ?? this.pinkInk,
      zincBg: zincBg ?? this.zincBg,
      zincInk: zincInk ?? this.zincInk,
      greenMain: greenMain ?? this.greenMain,
      amberMain: amberMain ?? this.amberMain,
      redMain: redMain ?? this.redMain,
      redBg: redBg ?? this.redBg,
      redInk: redInk ?? this.redInk,
    );
  }

  /// Colours are discrete brand primitives; lerp snaps to [other] at t >= 0.5
  /// rather than interpolating (no meaningful in-between brand colour).
  @override
  AssenColors lerp(ThemeExtension<AssenColors>? other, double t) {
    if (other is! AssenColors || t < 0.5) return this;
    return AssenColors(
      white: other.white,
      neutral50: other.neutral50,
      neutral100: other.neutral100,
      neutral200: other.neutral200,
      neutral300: other.neutral300,
      ink400: other.ink400,
      ink500: other.ink500,
      ink600: other.ink600,
      ink900: other.ink900,
      darkBg: other.darkBg,
      darkSurface: other.darkSurface,
      darkSurfaceHigh: other.darkSurfaceHigh,
      darkBorder: other.darkBorder,
      darkInk: other.darkInk,
      darkInkSub: other.darkInkSub,
      indigo100: other.indigo100,
      indigo500: other.indigo500,
      indigo600: other.indigo600,
      indigoHover: other.indigoHover,
      indigoInk: other.indigoInk,
      indigoDarkContainer: other.indigoDarkContainer,
      indigoOnDarkContainer: other.indigoOnDarkContainer,
      lavenderBg: other.lavenderBg,
      lavenderInk: other.lavenderInk,
      violetBg: other.violetBg,
      violetInk: other.violetInk,
      creamBg: other.creamBg,
      creamInk: other.creamInk,
      mintBg: other.mintBg,
      mintInk: other.mintInk,
      skyBg: other.skyBg,
      skyInk: other.skyInk,
      pinkBg: other.pinkBg,
      pinkInk: other.pinkInk,
      zincBg: other.zincBg,
      zincInk: other.zincInk,
      greenMain: other.greenMain,
      amberMain: other.amberMain,
      redMain: other.redMain,
      redBg: other.redBg,
      redInk: other.redInk,
    );
  }
}

/// Spacing scale exposed as a [ThemeExtension]. Values come from [SpacingTokens].
final class AssenSpacing extends ThemeExtension<AssenSpacing> {
  const AssenSpacing();

  /// 16px — the most common gutter (spacing.4).
  double get md => SpacingTokens.s4;

  @override
  AssenSpacing copyWith() => const AssenSpacing();

  @override
  AssenSpacing lerp(ThemeExtension<AssenSpacing>? other, double t) => this;
}

/// Corner radii exposed as a [ThemeExtension]. Values come from [RadiusTokens].
final class AssenRadius extends ThemeExtension<AssenRadius> {
  const AssenRadius();

  /// Card radius (radius.lg = 16px).
  double get card => RadiusTokens.lg;

  @override
  AssenRadius copyWith() => const AssenRadius();

  @override
  AssenRadius lerp(ThemeExtension<AssenRadius>? other, double t) => this;
}
