import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';

/// Acquisition state of an [AssenCollectionCell].
enum AssenCollectionState {
  /// 획득 — owned; the artwork shows in full colour.
  owned,

  /// 미획득 — not yet owned; a locked silhouette placeholder (references #5 —
  /// the collectible grid shows what is still to be earned).
  locked,
}

/// A collection grid cell (`획득 / 미획득(실루엣+잠금)` + NEW/한정 배지).
///
/// Covers the Domain/CollectionCell row of `components.md` — the cheki and badge
/// collection grids. An [AssenCollectionState.owned] cell shows its [artwork];
/// a [AssenCollectionState.locked] cell hides the artwork behind a muted
/// silhouette with a lock glyph so the grid communicates remaining goals
/// without revealing them. An optional corner [badge] (e.g. "NEW", "한정") uses
/// an [AssenBadge] — typically the strawberry key hue for NEW.
///
/// Pastel/ink discipline holds: the locked overlay is the ink ramp, never a
/// darkened artwork (tokens.md §1).
class AssenCollectionCell extends StatelessWidget {
  /// Creates a collection cell wrapping [artwork].
  ///
  /// [state] toggles the owned/locked rendering. [label] is shown under the
  /// tile. [badge] is an optional corner flag (NEW/한정). [onTap] opens the item.
  const AssenCollectionCell({
    required this.artwork,
    required this.label,
    this.state = AssenCollectionState.owned,
    this.badge,
    this.onTap,
    super.key,
  });

  /// The collectible artwork (image/illustration widget).
  final Widget artwork;

  /// The item label shown beneath the tile.
  final String label;

  /// Owned vs. locked rendering — see [AssenCollectionState].
  final AssenCollectionState state;

  /// Optional corner badge (e.g. a "NEW" [AssenBadge]).
  final AssenBadge? badge;

  /// Optional tap handler.
  final VoidCallback? onTap;

  bool get _locked => state == AssenCollectionState.locked;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final tile = AspectRatio(
      aspectRatio: 1,
      child: ClipRRect(
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        child: Stack(
          fit: StackFit.expand,
          children: [
            ColoredBox(
              color: colors.cream100,
              child: _locked
                  ? Center(
                      child: Icon(
                        Icons.lock_outline,
                        color: colors.ink300,
                        size: SpacingTokens.s8,
                      ),
                    )
                  : FittedBox(fit: BoxFit.cover, child: artwork),
            ),
            if (badge != null)
              Positioned(
                top: SpacingTokens.s1,
                left: SpacingTokens.s1,
                child: badge!,
              ),
          ],
        ),
      ),
    );

    final cell = Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        tile,
        const SizedBox(height: SpacingTokens.s1),
        Text(
          _locked ? '???' : label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            fontWeight: FontWeight.w600,
            color: _locked ? colors.ink500 : colors.ink900,
          ),
        ),
      ],
    );

    if (onTap == null) return cell;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: cell,
    );
  }
}
