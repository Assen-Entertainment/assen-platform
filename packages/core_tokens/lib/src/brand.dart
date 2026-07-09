// HAND-WRITTEN — NOT code-generated. Brand-expression tokens that the
// generated ref ramp (colors.gen.dart) deliberately does not carry.
//
// WHY this file is hand-authored (like color_scheme.dart): the platform's
// brand personality — a warm-paper canvas and the single sanctioned brand
// gradient — is not a raw palette primitive but a composed surface decision. It
// mirrors the web design system (web/src/styles: `--canvas` and
// `--gradient-brand`) so the mobile app reads with the SAME brand voice, not
// just the same hex ramp. The indigo palette itself stays untouched
// (docs/design/tokens.v2.json) — these are additive surface/decoration tokens
// layered on top of it.

import 'package:flutter/painting.dart';

/// Warm-paper canvas surface (mirrors web `--canvas: #f8f6f1`).
///
/// The app scaffold sits on [paper] instead of pure white so the white
/// design-system cards (AssenCard, product/post/membership surfaces) gain a
/// soft float/depth and an editorial rhythm — the web's "cards on paper" read.
/// It is intentionally near-white (a warm off-white), so body ink stays well
/// above AA on it: ink.900 (#191919) ≈ 15:1 and ink.600 (#52525B) ≈ 7:1 on
/// paper; secondary ink.500 clears AA (~4.5:1). Primary content still lives on
/// white cards.
abstract final class AssenSurfaces {
  /// The warm-paper scaffold canvas (#F8F6F1). White cards float on it.
  static const Color paper = Color(0xFFF8F6F1);
}

/// The single sanctioned brand gradient (mirrors web `--gradient-brand`).
///
/// APPROVED tokens.md exception 2026-07-09 — hero/cover/lockup/login ONLY; all
/// other fills stay solid. The design-system rule is "no decorative gradients"
/// (tokens.md §1); the CEO granted a bounded exception so the mobile app can
/// carry the web's brand front-door. Use it ONLY on: the Assen lockup tile, the
/// login/onboarding brand background, a creator cover fallback, and a single
/// discovery hero moment. Everywhere else, fills remain solid tokens.
abstract final class AssenGradients {
  /// Indigo-500 (#5A4DF0) → violet (#8A5CF7) at 135° — identical to the web
  /// `linear-gradient(135deg, #5a4df0 0%, #8a5cf7 100%)`. topLeft → bottomRight
  /// reproduces the CSS 135° angle. The violet stop is the gradient's terminal
  /// hue (web `--gradient-brand`), not a new palette primitive.
  static const LinearGradient brand = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF5A4DF0), Color(0xFF8A5CF7)],
  );

  /// White text/marks read on the brand gradient at any stop (contrast ≥ 5.6:1
  /// against indigo.500 and ≥ 4.6:1 against the violet terminal).
  static const Color onBrand = Color(0xFFFFFFFF);
}
