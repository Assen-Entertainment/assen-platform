// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.json (W3C DTCG 2025.10).
// Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).

import 'package:flutter/painting.dart';

/// Typography primitives (typography.*) — SSOT mirror of docs/design/tokens.md
/// §3. Font sizes are in logical pixels; [TextStyle] composites pair each scale
/// slot with its family stack, line height and weight. Widgets that only need a
/// size read `*Size`; new code can take the whole composed style.
abstract final class TypographyTokens {
  /// typography.fontFamily.display — primary face.
  ///
  /// Pinned to the bundled static 'Pretendard' (ui_kit/pubspec.yaml). The source
  /// listed 'Pretendard Variable' first, but no Variable face is bundled, so the
  /// display scale silently fell back; using the bundled family makes the
  /// display type actually render Pretendard (docs/design/tokens.v2.json updated
  /// to match — 2026-07-09).
  static const String displayFontFamily = 'Pretendard';

  /// typography.fontFamily.display — fallback stack (after the primary).
  static const List<String> displayFontFamilyFallback = [
    'Apple SD Gothic Neo',
    'sans-serif',
  ];

  /// typography.fontFamily.body — primary face.
  static const String bodyFontFamily = 'Pretendard';

  /// typography.fontFamily.body — fallback stack (after the primary).
  static const List<String> bodyFontFamilyFallback = [
    'Apple SD Gothic Neo',
    'sans-serif',
  ];

  /// typography.fontFamily.pixel — primary face.
  static const String pixelFontFamily = 'Galmuri11';

  /// typography.fontFamily.pixel — fallback stack (after the primary).
  static const List<String> pixelFontFamilyFallback = ['monospace'];

  /// typography.scale.displayL — 36px.
  static const double displayLSize = 36;

  /// typography.scale.displayM — 28px.
  static const double displayMSize = 28;

  /// typography.scale.displayS — 24px.
  static const double displaySSize = 24;

  /// typography.scale.headline — 22px.
  static const double headlineSize = 22;

  /// typography.scale.titleL — 19px.
  static const double titleLSize = 19;

  /// typography.scale.titleM — 16px.
  static const double titleMSize = 16;

  /// typography.scale.bodyL — 16px.
  static const double bodyLSize = 16;

  /// typography.scale.bodyM — 14px.
  static const double bodyMSize = 14;

  /// typography.scale.bodyS — 12px.
  static const double bodySSize = 12;

  /// typography.scale.label — 13px.
  static const double labelSize = 13;

  /// typography.scale.captionMicro — 11px.
  static const double captionMicroSize = 11;

  /// typography.scale.pixel — 11px.
  static const double pixelSize = 11;

  /// typography.scale.displayL — composed display 36px style.
  static const TextStyle displayL = TextStyle(
    fontFamily: displayFontFamily,
    fontFamilyFallback: displayFontFamilyFallback,
    fontSize: 36,
    height: 1.28,
    fontWeight: FontWeight.w700,
  );

  /// typography.scale.displayM — composed display 28px style.
  static const TextStyle displayM = TextStyle(
    fontFamily: displayFontFamily,
    fontFamilyFallback: displayFontFamilyFallback,
    fontSize: 28,
    height: 1.36,
    fontWeight: FontWeight.w700,
  );

  /// typography.scale.displayS — composed display 24px style.
  static const TextStyle displayS = TextStyle(
    fontFamily: displayFontFamily,
    fontFamilyFallback: displayFontFamilyFallback,
    fontSize: 24,
    height: 1.33,
    fontWeight: FontWeight.w700,
  );

  /// typography.scale.headline — composed display 22px style.
  static const TextStyle headline = TextStyle(
    fontFamily: displayFontFamily,
    fontFamilyFallback: displayFontFamilyFallback,
    fontSize: 22,
    height: 1.36,
    fontWeight: FontWeight.w700,
  );

  /// typography.scale.titleL — composed body 19px style.
  static const TextStyle titleL = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 19,
    height: 1.42,
    fontWeight: FontWeight.w600,
  );

  /// typography.scale.titleM — composed body 16px style.
  static const TextStyle titleM = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 16,
    height: 1.5,
    fontWeight: FontWeight.w600,
  );

  /// typography.scale.bodyL — composed body 16px style.
  static const TextStyle bodyL = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 16,
    height: 1.62,
    fontWeight: FontWeight.w400,
  );

  /// typography.scale.bodyM — composed body 14px style.
  static const TextStyle bodyM = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 14,
    height: 1.57,
    fontWeight: FontWeight.w400,
  );

  /// typography.scale.bodyS — composed body 12px style.
  static const TextStyle bodyS = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 12,
    height: 1.5,
    fontWeight: FontWeight.w400,
  );

  /// typography.scale.label — composed body 13px style.
  static const TextStyle label = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 13,
    height: 1.38,
    fontWeight: FontWeight.w500,
  );

  /// typography.scale.captionMicro — composed body 11px style.
  static const TextStyle captionMicro = TextStyle(
    fontFamily: bodyFontFamily,
    fontFamilyFallback: bodyFontFamilyFallback,
    fontSize: 11,
    height: 1.45,
    fontWeight: FontWeight.w500,
  );

  /// typography.scale.pixel — composed pixel 11px style.
  static const TextStyle pixel = TextStyle(
    fontFamily: pixelFontFamily,
    fontFamilyFallback: pixelFontFamilyFallback,
    fontSize: 11,
    height: 1.45,
    fontWeight: FontWeight.w400,
  );
}
