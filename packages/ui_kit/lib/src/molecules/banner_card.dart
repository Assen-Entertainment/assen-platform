import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 title.l/body.m).
const double _bannerTitleSize = 19; // tokens.md §3 title.l — banner headline
const double _bannerSubtitleSize = 14; // tokens.md §3 body.m — banner detail

/// A home banner card for the carousel (`홈 배너`).
///
/// Covers the Content/BannerCard row of `components.md` — the home banner
/// carousel (pairs with the `AssenPageIndicator` atom). It is a wide rounded
/// card carrying a [background] (image/colour fill) with the [title]/[subtitle]
/// laid over a bottom scrim so the copy stays legible on any artwork. The scrim
/// is a translucent ink wash, not a gradient brand effect (tokens.md — no
/// decorative gradients); it exists purely for text contrast.
class AssenBannerCard extends StatelessWidget {
  /// Creates a banner card titled [title] over [background].
  ///
  /// [subtitle] is optional supporting copy. [onTap] opens the banner target.
  /// [aspectRatio] defaults to a wide 16:9 hero.
  const AssenBannerCard({
    required this.title,
    required this.background,
    this.subtitle,
    this.onTap,
    this.aspectRatio = 16 / 9,
    super.key,
  });

  /// The banner headline.
  final String title;

  /// The background widget (image, illustration or colour fill).
  final Widget background;

  /// Optional supporting copy under the title.
  final String? subtitle;

  /// Optional tap handler.
  final VoidCallback? onTap;

  /// Card aspect ratio — defaults to a 16:9 hero.
  final double aspectRatio;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final card = AspectRatio(
      aspectRatio: aspectRatio,
      child: ClipRRect(
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        child: Stack(
          fit: StackFit.expand,
          children: [
            ColoredBox(
              color: colors.strawberryBg,
              child: FittedBox(fit: BoxFit.cover, child: background),
            ),
            // Bottom scrim purely for text legibility (not a brand gradient).
            const _Scrim(),
            Positioned(
              left: SpacingTokens.s4,
              right: SpacingTokens.s4,
              bottom: SpacingTokens.s4,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: _bannerTitleSize,
                      fontWeight: FontWeight.w700,
                      color: colors.white,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: SpacingTokens.s1),
                    Text(
                      subtitle!,
                      style: TextStyle(
                        fontSize: _bannerSubtitleSize,
                        color: colors.white,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );

    if (onTap == null) return card;
    return GestureDetector(onTap: onTap, child: card);
  }
}

/// A bottom-anchored translucent ink wash that keeps overlaid copy legible.
///
/// This is a contrast utility — a single solid colour at low opacity behind the
/// text band — not a decorative gradient (tokens.md forbids brand gradients).
class _Scrim extends StatelessWidget {
  const _Scrim();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Align(
      alignment: Alignment.bottomCenter,
      child: FractionallySizedBox(
        heightFactor: 0.5,
        widthFactor: 1,
        child: ColoredBox(
          // ink.900 at ~40% — a flat scrim for text contrast only.
          color: colors.ink900.withValues(alpha: 0.4),
        ),
      ),
    );
  }
}
