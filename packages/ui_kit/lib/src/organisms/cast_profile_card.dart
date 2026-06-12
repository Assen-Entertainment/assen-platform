import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/atoms/favorite_button.dart';

/// A cast member profile card (`기본/최애♥/출근중`).
///
/// Covers the Domain/CastProfileCard row of `components.md` and the cast list
/// (screens.md C2/C3). It composes an [AssenAvatar] (carrying the cast's identity
/// [hue] ring and the 출근중 dot when [isOnShift]) with the [name], an optional
/// [tagline], and an [AssenFavoriteButton] for 최애 registration. Identity colour
/// is the cast's assigned pastel hue (응원색 culture — references #11), surfacing
/// the same hue on the avatar ring and an "출근중" pill — never a parasocial
/// closeness device (references 금지 #1).
class AssenCastProfileCard extends StatelessWidget {
  /// Creates a profile card for the cast [name].
  ///
  /// [hue] is the cast's identity colour. [isOnShift] adds the 출근중 marker;
  /// [isFavorite]/[onFavoriteChanged] drive the 최애 toggle. [tagline] is an
  /// optional one-line role/catchphrase. [imageProvider] supplies the photo
  /// (initials fall back when null). [onTap] opens the full profile.
  const AssenCastProfileCard({
    required this.name,
    required this.hue,
    required this.isFavorite,
    required this.onFavoriteChanged,
    this.isOnShift = false,
    this.tagline,
    this.imageProvider,
    this.onTap,
    super.key,
  });

  /// The cast member's name.
  final String name;

  /// The cast identity hue (응원색) used on the avatar ring and 출근중 pill.
  final AssenBadgeHue hue;

  /// Whether the cast is currently on shift (adds the 출근중 marker).
  final bool isOnShift;

  /// Whether this cast is the viewer's 최애.
  final bool isFavorite;

  /// Reports a 최애 toggle.
  final ValueChanged<bool>? onFavoriteChanged;

  /// Optional role/catchphrase line.
  final String? tagline;

  /// Optional avatar image; initials fall back when null.
  final ImageProvider<Object>? imageProvider;

  /// Opens the full cast profile.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      onTap: onTap,
      child: Row(
        children: [
          AssenAvatar(
            name: name,
            hue: hue,
            size: AssenAvatarSize.l,
            isOnline: isOnShift,
            imageProvider: imageProvider,
          ),
          const SizedBox(width: SpacingTokens.s4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: TypographyTokens.titleMSize,
                          fontWeight: FontWeight.w700,
                          color: colors.ink900,
                        ),
                      ),
                    ),
                    if (isOnShift) ...[
                      const SizedBox(width: SpacingTokens.s2),
                      const AssenBadge(
                        label: '출근중',
                        hue: AssenBadgeHue.matcha,
                      ),
                    ],
                  ],
                ),
                if (tagline != null) ...[
                  const SizedBox(height: SpacingTokens.s1),
                  Text(
                    tagline!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: TypographyTokens.bodySSize,
                      color: colors.ink700,
                    ),
                  ),
                ],
              ],
            ),
          ),
          AssenFavoriteButton(
            isFavorite: isFavorite,
            onChanged: onFavoriteChanged,
          ),
        ],
      ),
    );
  }
}
