// Unit tests for CreatorAccent: hex parsing, the invalid/null fallback, and the
// contrast-derived onAccent. Pure logic — no widget tree.

import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

const Color _white = Color(0xFFFFFFFF);
const Color _black = Color(0xFF000000);
const Color _rose = Color(0xFFE84E6F);

void main() {
  group('CreatorAccent.fromHex', () {
    test('parses a 6-digit hex into an opaque accent', () {
      final accent = CreatorAccent.fromHex(
        '#3366CC',
        surface: _white,
        fallback: _rose,
      );
      // Fully opaque regardless of the input's channel values.
      expect(accent.accent.a, 1.0);
      // onAccent is one of the two extremes it chooses between.
      expect(accent.onAccent == _white || accent.onAccent == _black, isTrue);
    });

    test('expands a 3-digit hex like the 6-digit form', () {
      final short = CreatorAccent.fromHex(
        '#39c',
        surface: _white,
        fallback: _rose,
      );
      final long = CreatorAccent.fromHex(
        '#3399cc',
        surface: _white,
        fallback: _rose,
      );
      expect(short.accent, long.accent);
    });

    test('an invalid hex falls back to the same accent as null', () {
      final bad = CreatorAccent.fromHex(
        'not-a-color',
        surface: _white,
        fallback: _rose,
      );
      final none = CreatorAccent.fromHex(
        null,
        surface: _white,
        fallback: _rose,
      );
      expect(bad.accent, none.accent);
    });

    test('a white base on a white surface is darkened to stay visible', () {
      final accent = CreatorAccent.fromHex(
        '#FFFFFF',
        surface: _white,
        fallback: _rose,
      );
      // ensureContrast must move it off white (1:1 contrast is invisible).
      expect(accent.accent, isNot(_white));
    });

    test('a black base yields white onAccent', () {
      final accent = CreatorAccent.fromHex(
        '#000000',
        surface: _white,
        fallback: _rose,
      );
      expect(accent.onAccent, _white);
    });
  });
}
