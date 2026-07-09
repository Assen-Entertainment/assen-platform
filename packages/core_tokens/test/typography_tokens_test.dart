// Snapshot guard for the GENERATED typography primitives (ASS-130). The scale
// mirrors docs/design/tokens.md §3; if tokens.json or the codegen projection
// drifts, these break. Sizes are the literals ui_kit used to hard-code, so the
// values here also pin the ui_kit replacement (visual result must not move).

import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TypographyTokens font sizes (tokens.md §3)', () {
    test('display + headline scale', () {
      expect(TypographyTokens.displayLSize, 36);
      expect(TypographyTokens.displayMSize, 28);
      expect(TypographyTokens.headlineSize, 22);
    });

    test('title scale', () {
      expect(TypographyTokens.titleLSize, 19);
      expect(TypographyTokens.titleMSize, 16);
    });

    test('body scale', () {
      expect(TypographyTokens.bodyLSize, 16);
      expect(TypographyTokens.bodyMSize, 14);
      expect(TypographyTokens.bodySSize, 12);
    });

    test('label + pixel scale', () {
      expect(TypographyTokens.labelSize, 13);
      expect(TypographyTokens.pixelSize, 11);
    });
  });

  group('TypographyTokens font families', () {
    test('display leads with Pretendard, falls back through the stack', () {
      // G012: display now sources from docs/design/tokens.v2.json (Pretendard),
      // not the dead tokens.json ("Cafe24 Ssurround"). The primary is the v2
      // "Pretendard Variable"; the bundled static Pretendard (ui_kit/fonts) is
      // reached via the fallback list.
      expect(TypographyTokens.displayFontFamily, 'Pretendard Variable');
      expect(
        TypographyTokens.displayFontFamilyFallback,
        const ['Pretendard', 'Apple SD Gothic Neo', 'sans-serif'],
      );
    });

    test('body is Pretendard, pixel is Galmuri11', () {
      expect(TypographyTokens.bodyFontFamily, 'Pretendard');
      expect(TypographyTokens.pixelFontFamily, 'Galmuri11');
    });
  });

  group('TypographyTokens composed TextStyles', () {
    test('bodyM pairs the family, size, height and weight', () {
      const style = TypographyTokens.bodyM;
      expect(style.fontFamily, TypographyTokens.bodyFontFamily);
      expect(style.fontFamilyFallback, TypographyTokens.bodyFontFamilyFallback);
      expect(style.fontSize, TypographyTokens.bodyMSize);
      expect(style.height, 1.57);
      expect(style.fontWeight, FontWeight.w400);
    });

    test('label is the medium-weight 13px button/chip/tab style', () {
      const style = TypographyTokens.label;
      expect(style.fontSize, TypographyTokens.labelSize);
      expect(style.fontWeight, FontWeight.w500);
    });

    test('displayL is the 700-weight display face', () {
      const style = TypographyTokens.displayL;
      expect(style.fontFamily, TypographyTokens.displayFontFamily);
      expect(style.fontSize, TypographyTokens.displayLSize);
      expect(style.fontWeight, FontWeight.w700);
    });
  });
}
