import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/src/creator_accent.dart';

void main() {
  // Representative creator colours incl. stress cases (very light, near-black).
  const cases = <Color>[
    Color(0xFF5A4DF0), // Assen Indigo
    Color(0xFF0E9E9E), // teal (Figma ThemeA)
    Color(0xFFE14B8A), // coral (Figma ThemeB)
    Color(0xFFF2C94C), // pale yellow — fails AA as UI on white
    Color(0xFF111111), // near-black
    Color(0xFFFFFFFF), // white
  ];

  group('CreatorAccent.fromBase', () {
    test('onAccent reaches at least UI contrast (3:1) on the accent fill', () {
      for (final base in cases) {
        final a = CreatorAccent.fromBase(base);
        expect(
          CreatorAccent.contrastRatio(a.accent, a.onAccent),
          greaterThanOrEqualTo(CreatorAccent.aaUi),
          reason: 'onAccent unreadable for $base',
        );
      }
    });

    test('onAccentContainer meets AA text contrast (4.5:1) on the container', () {
      for (final base in cases) {
        final a = CreatorAccent.fromBase(base);
        expect(
          CreatorAccent.contrastRatio(a.onAccentContainer, a.accentContainer),
          greaterThanOrEqualTo(CreatorAccent.aaText),
          reason: 'onAccentContainer fails AA for $base',
        );
      }
    });

    test('a pale accent is darkened so it stays a visible UI element on white', () {
      const pale = Color(0xFFF2C94C);
      final a = CreatorAccent.fromBase(pale);
      expect(
        CreatorAccent.contrastRatio(a.accent, const Color(0xFFFFFFFF)),
        greaterThanOrEqualTo(CreatorAccent.aaUi),
      );
    });

    test('dark-surface container blends against the dark ground', () {
      const base = Color(0xFF5A4DF0);
      const darkSurface = Color(0xFF141417);
      final a = CreatorAccent.fromBase(base, surface: darkSurface);
      // container is closer to the dark surface than to pure white
      expect(
        a.accentContainer.computeLuminance(),
        lessThan(0.5),
      );
    });
  });

  group('CreatorAccent.contrastRatio', () {
    test('black on white is 21:1', () {
      expect(
        CreatorAccent.contrastRatio(
          const Color(0xFF000000),
          const Color(0xFFFFFFFF),
        ),
        closeTo(21.0, 0.1),
      );
    });
  });
}
