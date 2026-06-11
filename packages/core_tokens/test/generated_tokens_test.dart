// Spot-checks that the GENERATED token primitives carry the exact values from
// docs/design/tokens.json. This guards the codegen projection (ASS-128): if the
// build script or the source drifts, these break. New coverage replacing the P0
// placeholder spacing test (whose `ofStep` API the generated class supersedes).

import 'dart:ui';

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('generated RefColors', () {
    test('rose.main is the solid CTA anchor #C2486B', () {
      expect(RefColors.roseMain, const Color(0xFFC2486B));
    });

    test('cream.50 app background is #FFFDF7', () {
      expect(RefColors.cream50, const Color(0xFFFFFDF7));
    });

    test('strawberry.bgSubtle is #FFF0F4', () {
      expect(RefColors.strawberryBgSubtle, const Color(0xFFFFF0F4));
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
      expect(ext.roseMain, RefColors.roseMain);
      expect(ext.skyInk, RefColors.skyInk);
    });

    test('AssenColors.lerp snaps to the target past the midpoint', () {
      const a = AssenColors();
      final b = a.copyWith(roseMain: const Color(0xFF000000));
      // t < 0.5 keeps `a`; t >= 0.5 takes `b` (discrete brand colours).
      expect(a.lerp(b, 0.4).roseMain, a.roseMain);
      expect(a.lerp(b, 0.6).roseMain, b.roseMain);
    });
  });

  group('hand-written AssenColorScheme', () {
    test('is light and primary maps to the generated rose', () {
      expect(AssenColorScheme.light.brightness, Brightness.light);
      expect(AssenColorScheme.light.primary, RefColors.roseMain);
    });

    test('surfaceTint is pinned to surface (M3 tint disabled)', () {
      expect(
        AssenColorScheme.light.surfaceTint,
        AssenColorScheme.light.surface,
      );
    });
  });
}
