// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.json (W3C DTCG 2025.10).
// Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).

import 'dart:ui';

/// Elevation shadow primitives (elevation.*). level0 has no shadow (outline
/// only); these are level1 (cards) and level2 (sheets/dialogs).
abstract final class ElevationTokens {
  /// 카드. level0은 그림자 없음+outline
  static const Color level1Color = Color(0x142B2724);
  static const double level1OffsetX = 0;
  static const double level1OffsetY = 2;
  static const double level1Blur = 8;
  static const double level1Spread = 0;

  /// 바텀시트·다이얼로그
  static const Color level2Color = Color(0x1F2B2724);
  static const double level2OffsetX = 0;
  static const double level2OffsetY = 8;
  static const double level2Blur = 24;
  static const double level2Spread = 0;
}
