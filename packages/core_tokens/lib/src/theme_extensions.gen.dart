// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.json (W3C DTCG 2025.10).
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
    this.cream50 = RefColors.cream50,
    this.cream100 = RefColors.cream100,
    this.cream200 = RefColors.cream200,
    this.cream300 = RefColors.cream300,
    this.white = RefColors.white,
    this.ink100 = RefColors.ink100,
    this.ink200 = RefColors.ink200,
    this.ink300 = RefColors.ink300,
    this.ink500 = RefColors.ink500,
    this.ink700 = RefColors.ink700,
    this.ink900 = RefColors.ink900,
    this.strawberryBgSubtle = RefColors.strawberryBgSubtle,
    this.strawberryBg = RefColors.strawberryBg,
    this.strawberryBorder = RefColors.strawberryBorder,
    this.strawberryInk = RefColors.strawberryInk,
    this.peachBgSubtle = RefColors.peachBgSubtle,
    this.peachBg = RefColors.peachBg,
    this.peachBorder = RefColors.peachBorder,
    this.peachInk = RefColors.peachInk,
    this.lemonBgSubtle = RefColors.lemonBgSubtle,
    this.lemonBg = RefColors.lemonBg,
    this.lemonBorder = RefColors.lemonBorder,
    this.lemonInk = RefColors.lemonInk,
    this.matchaBgSubtle = RefColors.matchaBgSubtle,
    this.matchaBg = RefColors.matchaBg,
    this.matchaBorder = RefColors.matchaBorder,
    this.matchaInk = RefColors.matchaInk,
    this.skyBgSubtle = RefColors.skyBgSubtle,
    this.skyBg = RefColors.skyBg,
    this.skyBorder = RefColors.skyBorder,
    this.skyInk = RefColors.skyInk,
    this.lavenderBgSubtle = RefColors.lavenderBgSubtle,
    this.lavenderBg = RefColors.lavenderBg,
    this.lavenderBorder = RefColors.lavenderBorder,
    this.lavenderInk = RefColors.lavenderInk,
    this.brassBg = RefColors.brassBg,
    this.brassMain = RefColors.brassMain,
    this.brassInk = RefColors.brassInk,
    this.redMain = RefColors.redMain,
    this.redBg = RefColors.redBg,
    this.redInk = RefColors.redInk,
    this.roseMain = RefColors.roseMain,
  });

  final Color cream50;
  final Color cream100;
  final Color cream200;
  final Color cream300;
  final Color white;
  final Color ink100;
  final Color ink200;
  final Color ink300;
  final Color ink500;
  final Color ink700;
  final Color ink900;
  final Color strawberryBgSubtle;
  final Color strawberryBg;
  final Color strawberryBorder;
  final Color strawberryInk;
  final Color peachBgSubtle;
  final Color peachBg;
  final Color peachBorder;
  final Color peachInk;
  final Color lemonBgSubtle;
  final Color lemonBg;
  final Color lemonBorder;
  final Color lemonInk;
  final Color matchaBgSubtle;
  final Color matchaBg;
  final Color matchaBorder;
  final Color matchaInk;
  final Color skyBgSubtle;
  final Color skyBg;
  final Color skyBorder;
  final Color skyInk;
  final Color lavenderBgSubtle;
  final Color lavenderBg;
  final Color lavenderBorder;
  final Color lavenderInk;
  final Color brassBg;
  final Color brassMain;
  final Color brassInk;
  final Color redMain;
  final Color redBg;
  final Color redInk;
  final Color roseMain;

  @override
  AssenColors copyWith({
    Color? cream50,
    Color? cream100,
    Color? cream200,
    Color? cream300,
    Color? white,
    Color? ink100,
    Color? ink200,
    Color? ink300,
    Color? ink500,
    Color? ink700,
    Color? ink900,
    Color? strawberryBgSubtle,
    Color? strawberryBg,
    Color? strawberryBorder,
    Color? strawberryInk,
    Color? peachBgSubtle,
    Color? peachBg,
    Color? peachBorder,
    Color? peachInk,
    Color? lemonBgSubtle,
    Color? lemonBg,
    Color? lemonBorder,
    Color? lemonInk,
    Color? matchaBgSubtle,
    Color? matchaBg,
    Color? matchaBorder,
    Color? matchaInk,
    Color? skyBgSubtle,
    Color? skyBg,
    Color? skyBorder,
    Color? skyInk,
    Color? lavenderBgSubtle,
    Color? lavenderBg,
    Color? lavenderBorder,
    Color? lavenderInk,
    Color? brassBg,
    Color? brassMain,
    Color? brassInk,
    Color? redMain,
    Color? redBg,
    Color? redInk,
    Color? roseMain,
  }) {
    return AssenColors(
      cream50: cream50 ?? this.cream50,
      cream100: cream100 ?? this.cream100,
      cream200: cream200 ?? this.cream200,
      cream300: cream300 ?? this.cream300,
      white: white ?? this.white,
      ink100: ink100 ?? this.ink100,
      ink200: ink200 ?? this.ink200,
      ink300: ink300 ?? this.ink300,
      ink500: ink500 ?? this.ink500,
      ink700: ink700 ?? this.ink700,
      ink900: ink900 ?? this.ink900,
      strawberryBgSubtle: strawberryBgSubtle ?? this.strawberryBgSubtle,
      strawberryBg: strawberryBg ?? this.strawberryBg,
      strawberryBorder: strawberryBorder ?? this.strawberryBorder,
      strawberryInk: strawberryInk ?? this.strawberryInk,
      peachBgSubtle: peachBgSubtle ?? this.peachBgSubtle,
      peachBg: peachBg ?? this.peachBg,
      peachBorder: peachBorder ?? this.peachBorder,
      peachInk: peachInk ?? this.peachInk,
      lemonBgSubtle: lemonBgSubtle ?? this.lemonBgSubtle,
      lemonBg: lemonBg ?? this.lemonBg,
      lemonBorder: lemonBorder ?? this.lemonBorder,
      lemonInk: lemonInk ?? this.lemonInk,
      matchaBgSubtle: matchaBgSubtle ?? this.matchaBgSubtle,
      matchaBg: matchaBg ?? this.matchaBg,
      matchaBorder: matchaBorder ?? this.matchaBorder,
      matchaInk: matchaInk ?? this.matchaInk,
      skyBgSubtle: skyBgSubtle ?? this.skyBgSubtle,
      skyBg: skyBg ?? this.skyBg,
      skyBorder: skyBorder ?? this.skyBorder,
      skyInk: skyInk ?? this.skyInk,
      lavenderBgSubtle: lavenderBgSubtle ?? this.lavenderBgSubtle,
      lavenderBg: lavenderBg ?? this.lavenderBg,
      lavenderBorder: lavenderBorder ?? this.lavenderBorder,
      lavenderInk: lavenderInk ?? this.lavenderInk,
      brassBg: brassBg ?? this.brassBg,
      brassMain: brassMain ?? this.brassMain,
      brassInk: brassInk ?? this.brassInk,
      redMain: redMain ?? this.redMain,
      redBg: redBg ?? this.redBg,
      redInk: redInk ?? this.redInk,
      roseMain: roseMain ?? this.roseMain,
    );
  }

  /// Colours are discrete brand primitives; lerp snaps to [other] at t >= 0.5
  /// rather than interpolating (no meaningful in-between brand colour).
  @override
  AssenColors lerp(ThemeExtension<AssenColors>? other, double t) {
    if (other is! AssenColors || t < 0.5) return this;
    return AssenColors(
      cream50: other.cream50,
      cream100: other.cream100,
      cream200: other.cream200,
      cream300: other.cream300,
      white: other.white,
      ink100: other.ink100,
      ink200: other.ink200,
      ink300: other.ink300,
      ink500: other.ink500,
      ink700: other.ink700,
      ink900: other.ink900,
      strawberryBgSubtle: other.strawberryBgSubtle,
      strawberryBg: other.strawberryBg,
      strawberryBorder: other.strawberryBorder,
      strawberryInk: other.strawberryInk,
      peachBgSubtle: other.peachBgSubtle,
      peachBg: other.peachBg,
      peachBorder: other.peachBorder,
      peachInk: other.peachInk,
      lemonBgSubtle: other.lemonBgSubtle,
      lemonBg: other.lemonBg,
      lemonBorder: other.lemonBorder,
      lemonInk: other.lemonInk,
      matchaBgSubtle: other.matchaBgSubtle,
      matchaBg: other.matchaBg,
      matchaBorder: other.matchaBorder,
      matchaInk: other.matchaInk,
      skyBgSubtle: other.skyBgSubtle,
      skyBg: other.skyBg,
      skyBorder: other.skyBorder,
      skyInk: other.skyInk,
      lavenderBgSubtle: other.lavenderBgSubtle,
      lavenderBg: other.lavenderBg,
      lavenderBorder: other.lavenderBorder,
      lavenderInk: other.lavenderInk,
      brassBg: other.brassBg,
      brassMain: other.brassMain,
      brassInk: other.brassInk,
      redMain: other.redMain,
      redBg: other.redBg,
      redInk: other.redInk,
      roseMain: other.roseMain,
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
