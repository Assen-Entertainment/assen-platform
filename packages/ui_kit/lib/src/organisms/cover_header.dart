import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A profile cover header: a banner strip with an overlapping avatar and an
/// identity block (title + optional badge + subtitle).
///
/// The mobile counterpart of the web discovery/profile header
/// (`creator-thumb-card` cover language): a full-bleed [coverImage] (falling
/// back to an [accent] wash) over which the [avatar] sits, half-overlapping the
/// banner, above a centred [title] (with an optional trailing [badge], e.g. a
/// verified mark) and [subtitle]. Domain-agnostic — the host screen supplies
/// the avatar/badge widgets and the accent; every colour/spacing is a token.
class AssenCoverHeader extends StatelessWidget {
  /// Creates a cover header titled [title].
  ///
  /// [coverImage] paints the banner; when null the banner is the sanctioned
  /// [gradient] (if set), else an [accent] wash, else the neutral surface.
  /// [avatar] overlaps the
  /// banner bottom; [badge] renders inline after the title; [subtitle] sits
  /// under it. [coverHeight] is the banner height.
  const AssenCoverHeader({
    required this.title,
    this.subtitle,
    this.avatar,
    this.badge,
    this.coverImage,
    this.coverSemanticLabel,
    this.accent,
    this.gradient,
    this.coverHeight = 140,
    super.key,
  });

  /// The centred profile title (e.g. the creator name).
  final String title;

  /// Optional secondary line under the title (e.g. `@handle · 카테고리`).
  final String? subtitle;

  /// Optional avatar widget overlapping the banner bottom.
  final Widget? avatar;

  /// Optional trailing badge shown inline after the title (e.g. verified mark).
  final Widget? badge;

  /// Optional banner image; when null an [accent]/surface wash is shown.
  final ImageProvider<Object>? coverImage;

  /// Optional screen-reader description for the banner (e.g. "미오 커버 이미지").
  ///
  /// Domain-agnostic: the host supplies the wording. When [coverImage] is set
  /// and this is null the banner is treated as decorative and hidden from
  /// screen readers; the fallback accent wash is always decorative.
  final String? coverSemanticLabel;

  /// Optional accent colour for the banner fallback wash.
  final Color? accent;

  /// Optional gradient for the banner fallback (used when there is no
  /// [coverImage]). A cover is one of the surfaces the tokens.md 2026-07-09
  /// exception sanctions for a gradient (pass [AssenGradients.brand] for a
  /// branded hero fallback); it takes precedence over [accent]. Everywhere
  /// without a cover image otherwise stays a solid [accent]/neutral wash.
  final Gradient? gradient;

  /// The banner height in logical pixels.
  final double coverHeight;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    // A cover image wins; otherwise the sanctioned [gradient] (if any) paints a
    // branded hero, falling back to the solid [accent]/neutral wash.
    final hasImage = coverImage != null;
    Widget cover = SizedBox(
      height: coverHeight,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: hasImage || gradient != null
              ? null
              : (accent ?? colors.neutral200),
          gradient: hasImage ? null : gradient,
          image: hasImage
              ? DecorationImage(image: coverImage!, fit: BoxFit.cover)
              : null,
        ),
      ),
    );
    // Label an informative banner for screen readers; a plain or unlabelled
    // banner (including the fallback accent wash) is treated as decorative.
    cover = coverImage != null && coverSemanticLabel != null
        ? Semantics(image: true, label: coverSemanticLabel, child: cover)
        : ExcludeSemantics(child: cover);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        cover,
        if (avatar != null)
          Transform.translate(
            offset: const Offset(0, -SpacingTokens.s6),
            child: Align(child: avatar),
          )
        else
          const SizedBox(height: SpacingTokens.s4),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.s4,
            0,
            SpacingTokens.s4,
            SpacingTokens.s4,
          ),
          child: Column(
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Flexible(
                    child: Semantics(
                      header: true,
                      child: Text(
                        title,
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: TypographyTokens.headlineSize,
                          fontWeight: FontWeight.w800,
                          color: colors.ink900,
                        ),
                      ),
                    ),
                  ),
                  if (badge != null) ...[
                    const SizedBox(width: SpacingTokens.s2),
                    badge!,
                  ],
                ],
              ),
              if (subtitle != null) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  subtitle!,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodyMSize,
                    color: colors.ink600,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
