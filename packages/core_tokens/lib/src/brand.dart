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
  ///
  /// GRAPHICS ONLY (not body text): measured contrast for [onBrand] white is
  /// ≈5.59:1 at the indigo.500 stop but only ≈4.24:1 at the violet terminal —
  /// below the 4.5:1 AA floor for body text (2026-07-10 a11y review). Safe for
  /// the lockup mark's stroke (a graphic, not text). Any surface that carries
  /// text over this gradient MUST use [brandScrimmed] instead.
  static const LinearGradient brand = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF5A4DF0), Color(0xFF8A5CF7)],
  );

  /// [brand], darkened by a flat 25% black scrim — mirrors the web bottom
  /// scrim (`from-black/25`) used behind text on `creator-home-header.tsx` /
  /// `discovery-view.tsx`. Alpha-compositing black at 25% over a colour is
  /// equivalent to scaling its channels by 0.75, so these are [brand]'s two
  /// stops pre-blended with that scrim — pixel-identical to stacking a real
  /// `Colors.black.withValues(alpha: 0.25)` layer on top, without the
  /// Stack/ClipRRect it would take to keep that layer inside the rounded
  /// corners. Applied UNIFORMLY (not a fade) so contrast holds regardless of
  /// where text falls on the gradient, per the 2026-07-10 a11y fix.
  ///
  /// Measured (WCAG relative luminance): ≈8.39:1 at the indigo.500 stop and
  /// ≈6.69:1 at the violet terminal — both clear the 4.5:1 AA floor with
  /// margin (the previous unscrimmed violet-stop reading was ≈4.24:1, a
  /// failure). Use this for every gradient surface that carries text: the
  /// login brand panel, the discovery hero band, and the creator cover
  /// fallback.
  static const LinearGradient brandScrimmed = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF443AB4), Color(0xFF6845B9)],
  );

  /// White text/marks read on [brand] at ≥4.24:1 (graphics only) and on
  /// [brandScrimmed] at ≥6.69:1 (safe for body text — see each field's doc).
  static const Color onBrand = Color(0xFFFFFFFF);
}
