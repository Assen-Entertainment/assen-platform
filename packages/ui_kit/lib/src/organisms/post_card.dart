import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A feed post card: a creator row, optional body + media, and like/comment
/// counts.
///
/// The mobile counterpart of the web `PostCard` (`web/src/components/ui/
/// post-card.tsx`): a full-width card with a creator header ([avatar] slot +
/// [creatorName] with an optional inline [verified] mark + optional
/// [creatorMeta] and [timeLabel]), an optional [body] paragraph, an optional
/// [media] banner, and a like/comment count footer. Domain-agnostic — the host
/// supplies the avatar widget and pre-formats every string; every colour,
/// spacing and radius is a token.
///
/// Browse-only (partial parity with the web card): the like/comment affordances
/// render as *static counts*, not buttons — there is no `onLike`/`onComment`
/// here. Interaction (liking, commenting) is an auth/payment gate not built on
/// mobile yet; [onTap] navigates to the post detail. [liked] only tints the
/// heart to reflect the caller's existing like state.
class AssenPostCard extends StatelessWidget {
  /// Creates a post card for [creatorName].
  ///
  /// [avatar] is the creator avatar slot; [creatorMeta] is a secondary identity
  /// line (e.g. `@handle`); [timeLabel] is a pre-formatted relative time;
  /// [verified] shows an inline verified mark after the name; [body] is the
  /// post
  /// text; [media] fills the media banner; [likeCount]/[commentCount] render as
  /// static counts and [liked] tints the heart. Pass [onTap] to open the post.
  const AssenPostCard({
    required this.creatorName,
    this.avatar,
    this.creatorMeta,
    this.timeLabel,
    this.verified = false,
    this.body,
    this.media,
    this.likeCount = 0,
    this.commentCount = 0,
    this.liked = false,
    this.onTap,
    super.key,
  });

  /// The creator's display name (clipped to one line).
  final String creatorName;

  /// Optional creator avatar widget shown leading the header.
  final Widget? avatar;

  /// Optional secondary identity line under the name (e.g. `@handle`).
  final String? creatorMeta;

  /// Optional pre-formatted relative time shown at the header trailing edge.
  final String? timeLabel;

  /// Whether to show an inline verified mark after the name.
  final bool verified;

  /// Optional post body text (wraps; preserves newlines).
  final String? body;

  /// Optional media widget filling the banner; hidden when null.
  final Widget? media;

  /// The like count shown in the footer (static — not a button).
  final int likeCount;

  /// The comment count shown in the footer (static — not a button).
  final int commentCount;

  /// Whether the caller has liked this post — tints the heart only.
  final bool liked;

  /// Optional tap handler; when set the whole card opens the post.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final content = Padding(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _Header(
            colors: colors,
            avatar: avatar,
            creatorName: creatorName,
            creatorMeta: creatorMeta,
            timeLabel: timeLabel,
            verified: verified,
          ),
          if (body != null && body!.isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.s3),
            Text(
              body!,
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                height: 1.5,
                color: colors.ink900,
              ),
            ),
          ],
          if (media != null) ...[
            const SizedBox(height: SpacingTokens.s3),
            ClipRRect(
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.md),
              ),
              child: AspectRatio(
                aspectRatio: 5 / 3,
                child: ColoredBox(color: colors.cream200, child: media),
              ),
            ),
          ],
          const SizedBox(height: SpacingTokens.s3),
          _CountFooter(
            colors: colors,
            likeCount: likeCount,
            commentCount: commentCount,
            liked: liked,
          ),
        ],
      ),
    );

    final card = DecoratedBox(
      decoration: BoxDecoration(
        color: colors.white,
        border: Border(bottom: BorderSide(color: colors.ink100)),
      ),
      child: content,
    );

    if (onTap == null) return card;
    return Material(
      type: MaterialType.transparency,
      child: InkWell(onTap: onTap, child: card),
    );
  }
}

/// The creator identity row: avatar, name (+ verified), meta, and time.
class _Header extends StatelessWidget {
  const _Header({
    required this.colors,
    required this.avatar,
    required this.creatorName,
    required this.creatorMeta,
    required this.timeLabel,
    required this.verified,
  });

  final AssenColors colors;
  final Widget? avatar;
  final String creatorName;
  final String? creatorMeta;
  final String? timeLabel;
  final bool verified;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (avatar != null) ...[
          avatar!,
          const SizedBox(width: SpacingTokens.s3),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Flexible(
                    child: Text(
                      creatorName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: TypographyTokens.titleMSize,
                        fontWeight: FontWeight.w600,
                        color: colors.ink900,
                      ),
                    ),
                  ),
                  if (verified) ...[
                    const SizedBox(width: SpacingTokens.s1),
                    Icon(
                      Icons.verified,
                      size: SpacingTokens.s4,
                      color: colors.skyInk,
                    ),
                  ],
                ],
              ),
              if (creatorMeta != null && creatorMeta!.isNotEmpty) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  creatorMeta!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (timeLabel != null && timeLabel!.isNotEmpty) ...[
          const SizedBox(width: SpacingTokens.s3),
          Text(
            timeLabel!,
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              color: colors.ink500,
            ),
          ),
        ],
      ],
    );
  }
}

/// The static like/comment count footer (display-only — no interaction).
class _CountFooter extends StatelessWidget {
  const _CountFooter({
    required this.colors,
    required this.likeCount,
    required this.commentCount,
    required this.liked,
  });

  final AssenColors colors;
  final int likeCount;
  final int commentCount;
  final bool liked;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _Count(
          icon: liked ? Icons.favorite : Icons.favorite_border,
          iconColor: liked ? colors.roseMain : colors.ink500,
          label: '$likeCount',
          colors: colors,
        ),
        const SizedBox(width: SpacingTokens.s5),
        _Count(
          icon: Icons.chat_bubble_outline,
          iconColor: colors.ink500,
          label: '$commentCount',
          colors: colors,
        ),
      ],
    );
  }
}

/// One icon + count pill in the footer.
class _Count extends StatelessWidget {
  const _Count({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.colors,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: SpacingTokens.s5, color: iconColor),
        const SizedBox(width: SpacingTokens.s1),
        Text(
          label,
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            color: colors.ink700,
          ),
        ),
      ],
    );
  }
}
