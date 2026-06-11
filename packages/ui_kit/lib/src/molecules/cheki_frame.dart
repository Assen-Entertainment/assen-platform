import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 pixel=11).
const double _chekiCaptionSize = 11; // tokens.md §3 pixel — handwritten caption

/// The instax-mini cheki frame motif (image slot + caption).
///
/// Covers the Domain/ChekiFrame row of `components.md` and the cheki motif in
/// `tokens.md` §5: the real film is 54×86 with a 46×62 image window and a
/// proportionally large lower margin (20/86) — that bottom band is the signature
/// "write your message here" strip. This widget reproduces those exact ratios
/// with an [AspectRatio] + [LayoutBuilder] (no package needed, per tokens.md),
/// so it scales to any width while staying photographically correct. It doubles
/// as the album grid cell.
///
/// Corners use [RadiusTokens.cheki] (2px — the physical film corner, not the UI
/// card radius). The caption renders in the pixel face for the retro feel.
class AssenChekiFrame extends StatelessWidget {
  /// Creates a cheki frame wrapping [image] in the photo window.
  ///
  /// [caption] is the optional message in the lower band. [onTap] makes the
  /// frame tappable (album cell). [rotation] (radians) lets a gallery scatter
  /// frames slightly for the physical-print feel.
  const AssenChekiFrame({
    required this.image,
    this.caption,
    this.onTap,
    this.rotation = 0,
    super.key,
  });

  /// The photo to show in the image window.
  final Widget image;

  /// Optional handwritten-style caption in the lower band.
  final String? caption;

  /// Optional tap handler (album cell use).
  final VoidCallback? onTap;

  /// Optional rotation in radians for a scattered gallery look.
  final double rotation;

  // instax mini real measurements (mm), used as pure ratios (tokens.md §5):
  // film 54×86, image window 46×62. The horizontal margin is (54-46)/2 = 4.
  static const double _filmW = 54;
  static const double _filmH = 86;
  static const double _imageW = 46;
  static const double _imageH = 62;
  static const double _sideMargin = (_filmW - _imageW) / 2; // 4
  static const double _topMargin = _sideMargin; // square top/side border

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final frame = AspectRatio(
      aspectRatio: _filmW / _filmH,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final unit = constraints.maxWidth / _filmW; // px per mm
          return DecoratedBox(
            decoration: BoxDecoration(
              color: colors.white,
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.cheki),
              ),
              boxShadow: const [
                BoxShadow(
                  color: ElevationTokens.level1Color,
                  offset: Offset(
                    ElevationTokens.level1OffsetX,
                    ElevationTokens.level1OffsetY,
                  ),
                  blurRadius: ElevationTokens.level1Blur,
                ),
              ],
            ),
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                _sideMargin * unit,
                _topMargin * unit,
                _sideMargin * unit,
                0,
              ),
              child: Column(
                children: [
                  SizedBox(
                    width: _imageW * unit,
                    height: _imageH * unit,
                    child: ColoredBox(
                      color: colors.ink100,
                      child: FittedBox(
                        fit: BoxFit.cover,
                        clipBehavior: Clip.hardEdge,
                        child: image,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: caption == null
                          ? const SizedBox.shrink()
                          : Padding(
                              padding: EdgeInsets.symmetric(
                                horizontal: _sideMargin * unit,
                              ),
                              child: Text(
                                caption!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: _chekiCaptionSize,
                                  color: colors.ink700,
                                ),
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );

    final rotated = rotation == 0
        ? frame
        : Transform.rotate(angle: rotation, child: frame);

    if (onTap == null) return rotated;
    return GestureDetector(onTap: onTap, child: rotated);
  }
}
