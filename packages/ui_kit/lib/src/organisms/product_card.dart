import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';

/// A monetizable-item card: media over a tag, title, optional meta, and price.
///
/// The mobile counterpart of the web `MonetizableItem` (goods/digital/ticket…):
/// a full-width card with a [media] banner (falling back to a cream
/// placeholder), a [tagLabel] pill, a one-line [title], an optional [meta]
/// line, and a [priceLabel]. Domain-agnostic — the host formats the price and
/// picks the tag; every colour/spacing/radius is a token. [onTap] makes the
/// whole card tappable.
class AssenProductCard extends StatelessWidget {
  /// Creates a product card titled [title] priced [priceLabel].
  ///
  /// [tagLabel] is the category pill (omit for none); [meta] is a secondary
  /// line; [media] is an optional thumbnail widget shown in the banner. Pass
  /// [onTap] to make the card interactive.
  const AssenProductCard({
    required this.title,
    required this.priceLabel,
    this.tagLabel,
    this.meta,
    this.media,
    this.onTap,
    super.key,
  });

  /// The product title (clipped to one line).
  final String title;

  /// The pre-formatted price (e.g. `₩12,000`).
  final String priceLabel;

  /// Optional category tag rendered as a pastel badge.
  final String? tagLabel;

  /// Optional secondary line under the title.
  final String? meta;

  /// Optional thumbnail widget filling the banner; a placeholder shows if null.
  final Widget? media;

  /// Optional tap handler; when set the whole card is tappable.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        AspectRatio(
          aspectRatio: 5 / 3,
          child: ColoredBox(
            color: colors.cream200,
            child: media,
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(SpacingTokens.s3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (tagLabel != null) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: AssenBadge(label: tagLabel!),
                ),
                const SizedBox(height: SpacingTokens.s2),
              ],
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w600,
                  color: colors.ink900,
                ),
              ),
              if (meta != null) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  meta!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
              const SizedBox(height: SpacingTokens.s2),
              Text(
                priceLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
            ],
          ),
        ),
      ],
    );

    final card = DecoratedBox(
      decoration: BoxDecoration(
        color: colors.white,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        border: Border.all(color: colors.ink100),
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        child: content,
      ),
    );

    if (onTap == null) return card;
    return Material(
      type: MaterialType.transparency,
      child: InkWell(
        onTap: onTap,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        child: card,
      ),
    );
  }
}
