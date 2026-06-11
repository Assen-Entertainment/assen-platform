// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.json (W3C DTCG 2025.10).
// Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).

import 'dart:ui';

/// Raw reference colour ramp (color.ref.*) from the design token source.
///
/// These are primitives only — semantic M3 roles (color.sys.*) and the
/// ColorScheme are deliberately NOT generated (a seeded M3 scheme distorts the
/// cream surface; see docs/design/tokens.md and ADR-0004). Consume these via
/// [AssenColors] (ThemeExtension) or directly for decorative motifs.
abstract final class RefColors {
  /// 앱 배경
  static const Color cream50 = Color(0xFFFFFDF7);

  static const Color cream100 = Color(0xFFFFF8E7);

  static const Color cream200 = Color(0xFFF8EFDB);

  static const Color cream300 = Color(0xFFEFE3C9);

  static const Color white = Color(0xFFFFFFFF);

  static const Color ink100 = Color(0xFFF0EADD);

  static const Color ink200 = Color(0xFFE3DACA);

  static const Color ink300 = Color(0xFFC9C0B4);

  /// 비활성·힌트 전용, 본문 금지
  static const Color ink500 = Color(0xFF8A8178);

  static const Color ink700 = Color(0xFF57534E);

  static const Color ink900 = Color(0xFF2B2724);

  static const Color strawberryBgSubtle = Color(0xFFFFF0F4);

  static const Color strawberryBg = Color(0xFFFFD9E2);

  static const Color strawberryBorder = Color(0xFFF0A8BC);

  static const Color strawberryInk = Color(0xFF8E2F4A);

  static const Color peachBgSubtle = Color(0xFFFFF2E9);

  static const Color peachBg = Color(0xFFFFDCC7);

  static const Color peachBorder = Color(0xFFEBAF85);

  static const Color peachInk = Color(0xFF8A4A1F);

  static const Color lemonBgSubtle = Color(0xFFFFF9DF);

  static const Color lemonBg = Color(0xFFFFEFB3);

  static const Color lemonBorder = Color(0xFFDDC25E);

  static const Color lemonInk = Color(0xFF6E5A14);

  static const Color matchaBgSubtle = Color(0xFFEFF6EA);

  static const Color matchaBg = Color(0xFFD8EBCB);

  static const Color matchaBorder = Color(0xFFA0CC89);

  static const Color matchaInk = Color(0xFF3E6132);

  static const Color skyBgSubtle = Color(0xFFEAF5F9);

  static const Color skyBg = Color(0xFFCFE9F2);

  static const Color skyBorder = Color(0xFF92C6D9);

  static const Color skyInk = Color(0xFF1F566B);

  static const Color lavenderBgSubtle = Color(0xFFF4F0FA);

  static const Color lavenderBg = Color(0xFFE2DAF4);

  static const Color lavenderBorder = Color(0xFFBCA9E3);

  static const Color lavenderInk = Color(0xFF54408A);

  static const Color brassBg = Color(0xFFF6ECD9);

  /// 장식 전용, 텍스트 금지
  static const Color brassMain = Color(0xFFD4A24F);

  static const Color brassInk = Color(0xFF6E5224);

  static const Color redMain = Color(0xFFB64650);

  static const Color redBg = Color(0xFFFFE1E4);

  static const Color redInk = Color(0xFF7A2530);

  /// CTA 앵커 — 유일한 솔리드 액션 컬러
  static const Color roseMain = Color(0xFFC2486B);
}
