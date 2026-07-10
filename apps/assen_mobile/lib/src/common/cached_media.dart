import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A disk + memory cached network image for post/product media banners (R10,
/// ASS-249).
///
/// Wraps [CachedNetworkImage] with the app's shared media policy so every
/// banner behaves the same: a neutral ([AssenColors.neutral200]) placeholder
/// while the bytes stream in, the same neutral fallback on a load failure (a
/// broken URL degrades to the same neutral banner an absent URL shows — R9a
/// errorBuilder parity), and a short cross-fade in. The bytes are cached to
/// disk and memory by `cached_network_image`, so a re-scroll or revisit paints
/// instantly instead of refetching.
///
/// Callers gate a null/empty URL to a plain placeholder upstream (the media
/// slot stays null), so [url] is always a real, non-empty URL here.
/// [semanticLabel] describes the media for screen readers (e.g. the item
/// title); when null the image is announced generically by the platform. The
/// label rides only on a successful load (via [buildLoadedImage] / the
/// `imageBuilder`), so the cream placeholder and error fallback are never
/// announced as an image — a broken URL degrades silently instead of
/// mislabelling the cream banner as the item (F1).
class CachedMedia extends StatelessWidget {
  /// Creates a cached media image for [url].
  const CachedMedia({required this.url, this.semanticLabel, super.key});

  /// The image URL. Non-empty — callers map null/empty to a null media slot.
  final String url;

  /// Optional screen-reader description of the media (e.g. the item title).
  final String? semanticLabel;

  /// Builds the resolved-image subtree once the bytes load, tagging it with the
  /// success-only [Semantics] image label. Wired as the `imageBuilder` so the
  /// label never leaks onto the loading/error cream fallback (F1); exposed for
  /// test to exercise the labelled success path without a network fetch.
  @visibleForTesting
  Widget buildLoadedImage(BuildContext context, ImageProvider imageProvider) {
    final image = Image(image: imageProvider, fit: BoxFit.cover);
    if (semanticLabel == null) return image;
    return Semantics(image: true, label: semanticLabel, child: image);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return CachedNetworkImage(
      imageUrl: url,
      fadeInDuration: MotionDurations.standard,
      // Explicit: the library default fadeOutDuration is 1000ms, which would
      // make the cream placeholder linger as the image fades in (F2).
      fadeOutDuration: MotionDurations.standard,
      imageBuilder: buildLoadedImage,
      // The cream placeholder/error carry no image label (unlabelled
      // ColoredBox), so a load in progress or a failed load is never announced
      // as the item and stays visually identical to the "no image" banner.
      placeholder: (context, _) => ColoredBox(color: colors.neutral200),
      errorWidget: (context, _, _) => ColoredBox(color: colors.neutral200),
    );
  }
}
