import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// The six pastel hues a [AssenBadge] can take.
///
/// Each hue is a `bg + ink` pair from the token ramp; the badge fills with the
/// `bg` step and writes its label in the matching `ink` step (pastels are
/// surface-only — tokens.md §1). Cast members are assigned one of these hues as
/// an identity colour (references #11).
enum AssenBadgeHue {
  /// 하츠코이 strawberry — the brand key hue.
  strawberry,

  /// peach.
  peach,

  /// lemon.
  lemon,

  /// matcha (also the success hue).
  matcha,

  /// sky.
  sky,

  /// lavender.
  lavender,
}

/// A small pastel label chip (`hue` 6종).
///
/// Covers the Content/Badge row of `components.md`. Used for tags and category
/// labels. Fill + text are a single hue's `bg`/`ink` pair, so the contrast is
/// always AA (each ink is chosen for ≥4.5:1 on its bg — tokens.md §1). Solid
/// fill, no gradient.
class AssenBadge extends StatelessWidget {
  /// Creates a badge labelled [label] tinted with [hue].
  const AssenBadge({
    required this.label,
    this.hue = AssenBadgeHue.strawberry,
    super.key,
  });

  /// The badge text.
  final String label;

  /// Which pastel hue to use — see [AssenBadgeHue].
  final AssenBadgeHue hue;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (background, foreground, border) = _palette(colors);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s2,
        vertical: SpacingTokens.s1,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.xs)),
        border: Border.all(color: border),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: foreground,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          height: 1.2,
        ),
      ),
    );
  }

  (Color, Color, Color) _palette(AssenColors c) {
    return switch (hue) {
      AssenBadgeHue.strawberry => (
        c.strawberryBg,
        c.strawberryInk,
        c.strawberryBorder,
      ),
      AssenBadgeHue.peach => (c.peachBg, c.peachInk, c.peachBorder),
      AssenBadgeHue.lemon => (c.lemonBg, c.lemonInk, c.lemonBorder),
      AssenBadgeHue.matcha => (c.matchaBg, c.matchaInk, c.matchaBorder),
      AssenBadgeHue.sky => (c.skyBg, c.skyInk, c.skyBorder),
      AssenBadgeHue.lavender => (c.lavenderBg, c.lavenderInk, c.lavenderBorder),
    };
  }
}

/// A numeric notification badge (`숫자 99+` / dot).
///
/// Covers the Content/CountBadge row of `components.md` — tab and notification
/// counters. Renders a small rose pill with the count; when [count] exceeds
/// [max] it shows "max+" (e.g. "99+"). A zero count renders a bare dot, useful
/// for "unread, count unknown" indicators.
class AssenCountBadge extends StatelessWidget {
  /// Creates a count badge for [count].
  ///
  /// Counts above [max] are clamped to a "max+" label. A [count] of 0 renders a
  /// dot marker.
  const AssenCountBadge({required this.count, this.max = 99, super.key});

  /// The number to display. 0 renders a dot.
  final int count;

  /// Largest exact value before switching to "max+". Defaults to 99.
  final int max;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    if (count <= 0) {
      return Container(
        width: SpacingTokens.s2,
        height: SpacingTokens.s2,
        decoration: BoxDecoration(
          color: colors.roseMain,
          shape: BoxShape.circle,
        ),
      );
    }

    final text = count > max ? '$max+' : '$count';
    // 18 is the fixed pill diameter for a notification count — a component
    // metric, not a spacing-scale value (there is no 18 token).
    return Container(
      constraints: const BoxConstraints(minWidth: 18),
      height: 18,
      padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s1),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: colors.roseMain,
        borderRadius: const BorderRadius.all(
          Radius.circular(RadiusTokens.full),
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          height: 1,
        ),
      ),
    );
  }
}

/// Semantic status of a [AssenStatusBadge].
///
/// Each status maps to a fixed hue so colour reads consistently across
/// reservations and reports (`components.md` Feedback/StatusBadge).
enum AssenStatusKind {
  /// 확정 — confirmed (matcha, the success hue).
  confirmed,

  /// 대기 — pending (lemon).
  pending,

  /// 완료 — done (sky).
  done,

  /// 취소 — cancelled (red).
  cancelled,
}

/// A semantic status pill (확정/대기/완료/취소).
///
/// Covers the Feedback/StatusBadge row of `components.md`. Unlike [AssenBadge]
/// (free hue), the hue here is bound to meaning: confirmed=matcha,
/// pending=lemon, done=sky, cancelled=red. Fill is the status `bg`, text the
/// status `ink` — AA by construction.
class AssenStatusBadge extends StatelessWidget {
  /// Creates a status badge for [kind] with the given [label] (e.g. "예약 확정").
  const AssenStatusBadge({required this.kind, required this.label, super.key});

  /// The semantic status — drives the hue.
  final AssenStatusKind kind;

  /// Human-readable status text.
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (background, foreground, border) = _palette(colors);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s2,
        vertical: SpacingTokens.s1,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.xs)),
        border: Border.all(color: border),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: foreground,
          fontSize: 12,
          fontWeight: FontWeight.w700,
          height: 1.2,
        ),
      ),
    );
  }

  (Color, Color, Color) _palette(AssenColors c) {
    return switch (kind) {
      AssenStatusKind.confirmed => (c.matchaBg, c.matchaInk, c.matchaBorder),
      AssenStatusKind.pending => (c.lemonBg, c.lemonInk, c.lemonBorder),
      AssenStatusKind.done => (c.skyBg, c.skyInk, c.skyBorder),
      AssenStatusKind.cancelled => (c.redBg, c.redInk, c.redMain),
    };
  }
}
