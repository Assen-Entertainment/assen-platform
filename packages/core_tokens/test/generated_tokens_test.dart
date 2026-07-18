// Spot-checks that the GENERATED token primitives carry the exact values from
// the design token source. This guards the codegen projection (ASS-128 / G012):
// colours come from docs/design/tokens.v2.json (Assen Indigo); the other scales
// come from docs/design/tokens.json. If the build script or the source drifts,
// these break.

import 'dart:ui';

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('generated RefColors', () {
    test('indigo.500 is the Assen Indigo primary #5A4DF0', () {
      expect(RefColors.indigo500, const Color(0xFF5A4DF0));
    });

    test('neutral.100 secondary fill is #F4F4F5', () {
      expect(RefColors.neutral100, const Color(0xFFF4F4F5));
    });

    test('indigo.100 accent container is #EFEFFE', () {
      expect(RefColors.indigo100, const Color(0xFFEFEFFE));
    });
  });

  group('generated scales', () {
    test('spacing.4 resolves to 16 logical px', () {
      expect(SpacingTokens.s4, 16);
    });

    test('radius.full is the 999px pill', () {
      expect(RadiusTokens.full, 999);
    });

    test('motion.long is 450ms (cheki/stamp celebration)', () {
      expect(MotionDurations.long, const Duration(milliseconds: 450));
    });

    test('elevation.level1 alpha matches the DTCG hex8 (0x14)', () {
      // #2B272414 -> ARGB 0x142B2724.
      expect(ElevationTokens.level1Color, const Color(0x142B2724));
    });
  });

  group('generated ThemeExtensions', () {
    test('AssenColors defaults mirror RefColors', () {
      const ext = AssenColors();
      expect(ext.indigo500, RefColors.indigo500);
      expect(ext.skyInk, RefColors.skyInk);
    });

    test('AssenColors.lerp snaps to the target past the midpoint', () {
      const a = AssenColors();
      final b = a.copyWith(indigo500: const Color(0xFF000000));
      // t < 0.5 keeps `a`; t >= 0.5 takes `b` (discrete brand colours).
      expect(a.lerp(b, 0.4).indigo500, a.indigo500);
      expect(a.lerp(b, 0.6).indigo500, b.indigo500);
    });
  });

  group('hand-written AssenColorScheme', () {
    test('is light and primary maps to the generated indigo', () {
      expect(AssenColorScheme.light.brightness, Brightness.light);
      expect(AssenColorScheme.light.primary, RefColors.indigo500);
    });

    test('surfaceTint is pinned to surface (M3 tint disabled)', () {
      expect(
        AssenColorScheme.light.surfaceTint,
        AssenColorScheme.light.surface,
      );
    });
  });
}
