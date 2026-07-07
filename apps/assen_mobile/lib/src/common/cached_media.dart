import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A disk + memory cached network image for post/product media banners (R10,
/// ASS-249).
///
/// Wraps [CachedNetworkImage] with the app's shared media policy so every
/// banner behaves the same: a cream ([AssenColors.cream200]) placeholder while
/// the bytes stream in, the same cream fallback on a load failure (a broken URL
/// degrades to the identical cream banner an absent URL shows — R9a
/// errorBuilder parity), and a short cross-fade in. The bytes are cached to
/// disk and memory by `cached_network_image`, so a re-scroll or revisit paints
/// instantly instead of refetching.
///
/// Callers gate a null/empty URL to a plain placeholder upstream (the media
/// slot stays null), so [url] is always a real, non-empty URL here.
/// [semanticLabel] describes the media for screen readers (e.g. the item
/// title); when null the image is announced generically by the platform.
class CachedMedia extends StatelessWidget {
  /// Creates a cached media image for [url].
  const CachedMedia({required this.url, this.semanticLabel, super.key});

  /// The image URL. Non-empty — callers map null/empty to a null media slot.
  final String url;

  /// Optional screen-reader description of the media (e.g. the item title).
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final image = CachedNetworkImage(
      imageUrl: url,
      fit: BoxFit.cover,
      fadeInDuration: const Duration(milliseconds: 200),
      placeholder: (context, _) => ColoredBox(color: colors.cream200),
      // The cream fallback matches the "no image" banner, so a failed load is
      // visually identical to an absent one (no default broken-image glyph).
      errorWidget: (context, _, _) => ColoredBox(color: colors.cream200),
    );
    if (semanticLabel == null) return image;
    return Semantics(image: true, label: semanticLabel, child: image);
  }
}
