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
  /// [coverImage] paints the banner; when null the banner is an [accent] wash
  /// (or the cream surface if [accent] is also null). [avatar] overlaps the
  /// banner bottom; [badge] renders inline after the title; [subtitle] sits
  /// under it. [coverHeight] is the banner height.
  const AssenCoverHeader({
    required this.title,
    this.subtitle,
    this.avatar,
    this.badge,
    this.coverImage,
    this.accent,
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

  /// Optional accent colour for the banner fallback wash.
  final Color? accent;

  /// The banner height in logical pixels.
  final double coverHeight;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          height: coverHeight,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: accent ?? colors.cream200,
              image: coverImage == null
                  ? null
                  : DecorationImage(image: coverImage!, fit: BoxFit.cover),
            ),
          ),
        ),
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
                    color: colors.ink700,
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
