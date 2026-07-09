// GENERATED — DO NOT EDIT BY HAND (#32).
// Source: docs/design/tokens.v2.json (Assen Indigo — W3C DTCG 2025.10).
// Regenerate: dart run melos run codegen   (verify: melos run codegen:verify).

import 'dart:ui';

/// Raw reference colour ramp (color.ref.*) from the design token source.
///
/// These are primitives only — semantic M3 roles (color.sys.*) and the
/// ColorScheme are deliberately NOT generated (a seeded M3 scheme distorts the
/// surface tone; see docs/design/tokens.md and ADR-0004). Consume these via
/// [AssenColors] (ThemeExtension) or directly for decorative motifs.
abstract final class RefColors {
  /// 서피스 (Fanding 142회)
  static const Color white = Color(0xFFFFFFFF);

  static const Color neutral50 = Color(0xFFF8F8F9);

  /// 보조 필
  static const Color neutral100 = Color(0xFFF4F4F5);

  /// 보더/divider/보조서피스 (Fanding 실측, 보더 141·bg 20)
  static const Color neutral200 = Color(0xFFE9E9F1);

  static const Color neutral300 = Color(0xFFD4D4D8);

  /// 힌트/placeholder — a11y UI: 흰 3.40:1 · neutral.100 3.09:1. 구 #9292A2은 neutral.100서 2.79(미달) — 리뷰 2026-06-28 정정. 본문 금지
  static const Color ink400 = Color(0xFF8A8A9A);

  /// 보조 텍스트 — a11y AA: 흰 4.99:1 · neutral.100(#F4F4F5 필/고서피스) 4.54:1. 구 #747486은 neutral.100서 4.17(미달) — 어드버서리얼 리뷰 2026-06-28 정정
  static const Color ink500 = Color(0xFF6E6E80);

  /// 보조 강조 (파생)
  static const Color ink600 = Color(0xFF52525B);

  /// 본문·제목 (Fanding 실측 1793회)
  static const Color ink900 = Color(0xFF191919);

  /// 다크 베이스 (파생 — Fanding 공개사이트는 라이트)
  static const Color darkBg = Color(0xFF141417);

  static const Color darkSurface = Color(0xFF1C1C20);

  static const Color darkSurfaceHigh = Color(0xFF26262B);

  static const Color darkBorder = Color(0xFF34343A);

  static const Color darkInk = Color(0xFFF4F4F5);

  static const Color darkInkSub = Color(0xFFA1A1AA);

  /// accentContainer/필 (Fanding 실측)
  static const Color indigo100 = Color(0xFFEFEFFE);

  /// Assen Indigo — primary 액센트. 2026-06-28 브랜드 시그니처: Stripe #635BFF/범용 SaaS 인디고 탈피 위해 violet 방향 hue 미세시프트+심도. 흰 대비 5.6:1(구 #5E63F8 4.54→개선). 라이트/다크 불변. ※2026-07-09 대표 확정(Fanding 톤 유지 — 정본, 가역 아님)
  static const Color indigo500 = Color(0xFF5A4DF0);

  /// pressed (파생)
  static const Color indigo600 = Color(0xFF4B50E0);

  /// primary filled hover — Stripe식 색조 시프트(명도 -8%, opacity 대체). 흰(onPrimary) 대비 7.85:1(AA). 라이트/다크 공통(darken → 두 모드 모두 대비 상승으로 AA 보장; 다크 lighten은 흰 텍스트 4.5 미달).
  static const Color indigoHover = Color(0xFF3727ED);

  /// 강한 대비 필요 시 (파생)
  static const Color indigoInk = Color(0xFF2E2C8A);

  static const Color indigoDarkContainer = Color(0xFF2A2A52);

  static const Color indigoOnDarkContainer = Color(0xFFC7C9FF);

  static const Color lavenderBg = Color(0xFFEFEFFE);

  static const Color lavenderInk = Color(0xFF4338CA);

  /// Fanding 실측 퍼플 틴트
  static const Color violetBg = Color(0xFFF6EEFD);

  static const Color violetInk = Color(0xFF6D28D9);

  static const Color creamBg = Color(0xFFFFF9EB);

  static const Color creamInk = Color(0xFF926A14);

  static const Color mintBg = Color(0xFFE8FEF1);

  static const Color mintInk = Color(0xFF166534);

  static const Color skyBg = Color(0xFFE7F6FF);

  static const Color skyInk = Color(0xFF1F566B);

  static const Color pinkBg = Color(0xFFFFF2F2);

  static const Color pinkInk = Color(0xFF9F1239);

  static const Color zincBg = Color(0xFFF4F4FA);

  static const Color zincInk = Color(0xFF3F3F46);

  /// success (#22C55E → a11y 3.05:1)
  static const Color greenMain = Color(0xFF1DA951);

  /// warning — 라이트 warning 색. #CE8509(3.01:1, cream 컨테이너 위 2.86:1)은 비텍스트 3:1 미달 → #B8740A(white 3.79:1 / cream.bg 3.61:1, WCAG 1.4.11 통과)
  static const Color amberMain = Color(0xFFB8740A);

  /// error #EF4444 → a11y 4.53:1
  static const Color redMain = Color(0xFFD73D3D);

  static const Color redBg = Color(0xFFFFF2F2);

  static const Color redInk = Color(0xFF9F1239);
}
