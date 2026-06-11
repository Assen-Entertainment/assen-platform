import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3).
const double _cardNameSize = 18; // tokens.md §3 title.l — member name
const double _cardLabelSize = 11; // tokens.md §3 pixel — field labels
const double _cardNumberSize = 15; // tokens.md §3 body.l — membership number
const double _cardPointSize = 22; // tokens.md §3 display.m — point balance

/// The pastel skin of an [AssenMembershipCard] (`skin 3종`).
///
/// Tier is expressed by hue, never by going dark — the hierarchy "never
/// darkens" (tokens.md §5, references 금지 #6). Each skin is one pastel hue's
/// surface/border/ink triple from the token ramp.
enum AssenMembershipSkin {
  /// strawberry — 하츠코이 key hue (entry skin).
  strawberry,

  /// sky.
  sky,

  /// lavender.
  lavender,
}

/// The digital membership card (`디지털 회원증` — the signature component).
///
/// Covers the Domain/MembershipCard row of `components.md` and the home hero
/// (screens.md C0). It is the platform's signboard surface, modelled on the
/// PassKit storeCard 5-layer grammar (references §3, tokens.md §5): a strip
/// header (logo + tier), the main field (member [name] + [avatar]), up to four
/// secondary fields (here the [memberNumber] + [points]) and a QR entry button
/// wired to [onShowQr]. The [skin] tints the whole card via a single pastel hue
/// (solid colour fields only — no gradient, tokens.md §1).
class AssenMembershipCard extends StatelessWidget {
  /// Creates a membership card for [name].
  ///
  /// [memberNumber] is the formatted membership id (shown in the pixel face).
  /// [points] is the loyalty balance. [tierLabel] names the tier on the strip
  /// (e.g. "하츠코이"). [avatar] is the member's [AssenAvatar]; [onShowQr] opens
  /// the full QR (the `AssenQrDisplay`). [skin] picks the pastel hue.
  const AssenMembershipCard({
    required this.name,
    required this.memberNumber,
    required this.points,
    required this.tierLabel,
    required this.avatar,
    this.onShowQr,
    this.skin = AssenMembershipSkin.strawberry,
    super.key,
  });

  /// The member's display name.
  final String name;

  /// The formatted membership number (e.g. "0000 1234 5678").
  final String memberNumber;

  /// The loyalty point balance, pre-formatted (e.g. "1,280").
  final String points;

  /// The tier name shown on the strip (e.g. "하츠코이").
  final String tierLabel;

  /// The member avatar.
  final AssenAvatar avatar;

  /// Opens the full-screen QR (`AssenQrDisplay`); null hides the QR button.
  final VoidCallback? onShowQr;

  /// The pastel skin — see [AssenMembershipSkin].
  final AssenMembershipSkin skin;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (surface, border, ink) = _palette(colors);

    return Semantics(
      label: '$name 회원증, 멤버십 번호 $memberNumber',
      container: true,
      child: Container(
        decoration: BoxDecoration(
          color: surface,
          borderRadius: const BorderRadius.all(
            Radius.circular(RadiusTokens.xl),
          ),
          border: Border.all(color: border),
        ),
        padding: const EdgeInsets.all(SpacingTokens.s5),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Strip header — brand mark + tier name (PassKit layer 1/2).
            Row(
              children: [
                Icon(Icons.coffee_rounded, size: SpacingTokens.s5, color: ink),
                const SizedBox(width: SpacingTokens.s2),
                Text(
                  tierLabel,
                  style: TextStyle(
                    fontSize: _cardLabelSize,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.5,
                    color: ink,
                  ),
                ),
                const Spacer(),
                if (onShowQr != null)
                  AssenIconButton(
                    icon: Icons.qr_code_2,
                    semanticLabel: 'QR 회원증 보기',
                    color: ink,
                    onPressed: onShowQr,
                  ),
              ],
            ),
            const SizedBox(height: SpacingTokens.s4),
            // Primary field — avatar + member name (PassKit layer 3).
            Row(
              children: [
                avatar,
                const SizedBox(width: SpacingTokens.s3),
                Expanded(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: _cardNameSize,
                      fontWeight: FontWeight.w700,
                      color: colors.ink900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: SpacingTokens.s5),
            // Secondary fields — membership number + points (PassKit layer 4).
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: _Field(
                    label: 'MEMBER NO.',
                    ink: ink,
                    child: Text(
                      memberNumber,
                      style: TextStyle(
                        fontSize: _cardNumberSize,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1,
                        color: colors.ink900,
                      ),
                    ),
                  ),
                ),
                _Field(
                  label: 'POINT',
                  ink: ink,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  child: Text(
                    points,
                    style: TextStyle(
                      fontSize: _cardPointSize,
                      fontWeight: FontWeight.w800,
                      color: colors.ink900,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  (Color, Color, Color) _palette(AssenColors c) {
    return switch (skin) {
      AssenMembershipSkin.strawberry => (
        c.strawberryBg,
        c.strawberryBorder,
        c.strawberryInk,
      ),
      AssenMembershipSkin.sky => (c.skyBg, c.skyBorder, c.skyInk),
      AssenMembershipSkin.lavender => (
        c.lavenderBg,
        c.lavenderBorder,
        c.lavenderInk,
      ),
    };
  }
}

/// A labelled PassKit-style field: a small hue-ink caption over its value.
class _Field extends StatelessWidget {
  const _Field({
    required this.label,
    required this.child,
    required this.ink,
    this.crossAxisAlignment = CrossAxisAlignment.start,
  });

  final String label;
  final Widget child;
  final Color ink;
  final CrossAxisAlignment crossAxisAlignment;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: crossAxisAlignment,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: _cardLabelSize,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
            color: ink,
          ),
        ),
        const SizedBox(height: SpacingTokens.s1),
        child,
      ],
    );
  }
}
