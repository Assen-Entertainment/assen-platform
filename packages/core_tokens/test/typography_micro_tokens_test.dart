import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ASS-134 typography additions', () {
    test('displayS preserves the 24px onboarding slide headline slot', () {
      const style = TypographyTokens.displayS;

      expect(TypographyTokens.displaySSize, 24);
      expect(style.fontFamily, TypographyTokens.displayFontFamily);
      expect(style.fontSize, TypographyTokens.displaySSize);
      expect(style.fontWeight, FontWeight.w700);
    });

    test('captionMicro is the body-family functional 11px label slot', () {
      const style = TypographyTokens.captionMicro;

      expect(TypographyTokens.captionMicroSize, 11);
      expect(style.fontFamily, TypographyTokens.bodyFontFamily);
      expect(style.fontSize, TypographyTokens.captionMicroSize);
      expect(style.fontWeight, FontWeight.w500);
    });
  });
}
