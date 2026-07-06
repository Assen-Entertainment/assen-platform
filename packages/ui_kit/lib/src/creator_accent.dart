import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';

/// Minimum WCAG contrast for body text on its background (AA).
const double _aaText = 4.5;

/// Minimum WCAG contrast for a UI accent against its surface.
const double _aaUi = 3;

/// A creator's signature colour, corrected into an accessible accent set.
///
/// The Dart counterpart of the web `creator-accent.ts` helper (the web file
/// documents itself as a port of this one): a creator picks a single arbitrary
/// [accent] base colour and this derives a set that satisfies WCAG contrast on
/// the app's cream/white surfaces —
///
/// - [accent]: the base nudged in lightness to clear the UI contrast minimum
///   against the surface, so it is safe as a fill or emphasis colour.
/// - [onAccent]: black or white — whichever contrasts more with [accent] — for
///   text/icons drawn on top of it.
/// - [accentContainer]: the base tinted 12% into the surface (soft fill).
/// - [onAccentContainer]: the base darkened/lightened to clear AA text contrast
///   on [accentContainer].
///
/// This is a four-field set: the web `creator-accent.ts` also derives a fifth
/// `accentHover` for its CSS hover state, which this port omits (mobile has no
/// hover surface).
///
/// Apply it to creator-scoped chrome only (profile cover, follow CTA, verified
/// tint); global app chrome keeps the brand rose. An absent or unparseable base
/// falls back to a caller-supplied brand colour, so a bad `accent_color` never
/// throws or renders an invisible accent.
@immutable
class CreatorAccent {
  /// Creates a resolved accent set (usually via [CreatorAccent.fromHex]).
  const CreatorAccent({
    required this.accent,
    required this.onAccent,
    required this.accentContainer,
    required this.onAccentContainer,
  });

  /// Resolves an accent set from a creator's [hex] base against [surface].
  ///
  /// [hex] accepts `#RGB`, `RGB`, `#RRGGBB` or `RRGGBB` (case-insensitive); any
  /// other value — including null or a malformed string — degrades to
  /// [fallback] (pass the brand rose) so the result is always accessible.
  /// [surface] is the background the accent sits on (white/cream in this app).
  factory CreatorAccent.fromHex(
    String? hex, {
    required Color surface,
    required Color fallback,
  }) {
    final base = _parseHex(hex) ?? fallback;
    final accent = _ensureContrast(base, surface, _aaUi);
    final container = _mix(base, surface, 0.12);
    return CreatorAccent(
      accent: accent,
      onAccent: _bestOn(accent),
      accentContainer: container,
      onAccentContainer: _ensureContrast(base, container, _aaText),
    );
  }

  /// The contrast-corrected accent (fill/emphasis colour).
  final Color accent;

  /// Text/icon colour that reads on [accent] (black or white).
  final Color onAccent;

  /// A soft tinted background derived from the base.
  final Color accentContainer;

  /// Text/icon colour that reads on [accentContainer].
  final Color onAccentContainer;

  /// Parses a 3- or 6-digit hex string into a fully-opaque [Color], else null.
  static Color? _parseHex(String? hex) {
    if (hex == null) return null;
    var h = hex.trim();
    if (h.startsWith('#')) h = h.substring(1);
    if (h.length == 3) {
      h = h.split('').map((c) => '$c$c').join();
    }
    if (h.length != 6) return null;
    final value = int.tryParse(h, radix: 16);
    if (value == null) return null;
    return Color(0xFF000000 | value);
  }

  /// The WCAG contrast ratio (1..21) between two opaque colours.
  static double _contrast(Color a, Color b) {
    final la = a.computeLuminance();
    final lb = b.computeLuminance();
    final hi = la > lb ? la : lb;
    final lo = la > lb ? lb : la;
    return (hi + 0.05) / (lo + 0.05);
  }

  /// Nudges [fg]'s lightness until it clears [target] contrast on [bg].
  ///
  /// Moves away from [bg] (darker on a light surface, lighter on a dark one) in
  /// small steps, returning the first colour that clears [target] or the best
  /// found if the target is unreachable.
  static Color _ensureContrast(Color fg, Color bg, double target) {
    if (_contrast(fg, bg) >= target) return fg;
    final darken = bg.computeLuminance() > 0.5;
    final hsl = HSLColor.fromColor(fg);
    var best = fg;
    var bestContrast = _contrast(fg, bg);
    for (var i = 1; i <= 100; i++) {
      final lightness = (darken ? 0.5 - i * 0.005 : 0.5 + i * 0.005).clamp(
        0.0,
        1.0,
      );
      final candidate = hsl.withLightness(lightness).toColor();
      final contrast = _contrast(candidate, bg);
      if (contrast > bestContrast) {
        best = candidate;
        bestContrast = contrast;
      }
      if (contrast >= target) return candidate;
    }
    return best;
  }

  /// Black or white — whichever contrasts more with [accent].
  static Color _bestOn(Color accent) {
    const white = Color(0xFFFFFFFF);
    const black = Color(0xFF000000);
    return _contrast(white, accent) >= _contrast(black, accent) ? white : black;
  }

  /// Mixes [ratio] of [base] into [surface] (0 = surface, 1 = base).
  static Color _mix(Color base, Color surface, double ratio) =>
      Color.lerp(surface, base, ratio)!;
}
