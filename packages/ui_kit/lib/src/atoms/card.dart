import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Elevation level of an [AssenCard].
enum AssenCardLevel {
  /// level0 — no shadow, separated by an outline only. The default in this
  /// system, where borders (not shadows) do most of the separating
  /// (tokens.md §7).
  level0,

  /// level1 — a soft card shadow (`ElevationTokens.level1*`) for surfaces that
  /// should read as lifted off the cream background.
  level1,
}

/// A generic surface container (`level0` 보더 / `level1` 그림자).
///
/// Covers the Containment/Card row of `components.md`. Wraps content on a white
/// surface with the card radius; [level] chooses outline vs. shadow. The shadow
/// values come straight from [ElevationTokens] so the two-step elevation scale
/// (tokens.md §4) is never re-invented. [onTap] makes the whole card tappable
/// with a matching ink ripple.
class AssenCard extends StatelessWidget {
  /// Creates a card wrapping [child].
  ///
  /// [level] selects outline ([AssenCardLevel.level0]) or shadow
  /// ([AssenCardLevel.level1]). [padding] defaults to the 16px card inset
  /// (tokens.md §4). Pass [onTap] to make the card interactive.
  const AssenCard({
    required this.child,
    this.level = AssenCardLevel.level0,
    this.padding = const EdgeInsets.all(SpacingTokens.s4),
    this.onTap,
    super.key,
  });

  /// The card's content.
  final Widget child;

  /// Outline vs. shadow — see [AssenCardLevel].
  final AssenCardLevel level;

  /// Inner padding around [child]. Defaults to the 16px card inset.
  final EdgeInsetsGeometry padding;

  /// Optional tap handler; when set the whole card is tappable.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isLevel1 = level == AssenCardLevel.level1;

    final decoration = BoxDecoration(
      color: colors.white,
      borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
      border: isLevel1 ? null : Border.all(color: colors.ink100),
      boxShadow: isLevel1
          ? const [
              BoxShadow(
                color: ElevationTokens.level1Color,
                offset: Offset(
                  ElevationTokens.level1OffsetX,
                  ElevationTokens.level1OffsetY,
                ),
                blurRadius: ElevationTokens.level1Blur,
              ),
            ]
          : null,
    );

    final content = Padding(padding: padding, child: child);

    return DecoratedBox(
      decoration: decoration,
      child: onTap == null
          ? content
          : Material(
              type: MaterialType.transparency,
              child: InkWell(
                onTap: onTap,
                borderRadius: const BorderRadius.all(
                  Radius.circular(RadiusTokens.lg),
                ),
                child: content,
              ),
            ),
    );
  }
}
