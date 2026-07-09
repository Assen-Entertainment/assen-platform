import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A heart toggle for marking a cast member as 최애 (favourite).
///
/// Covers the Domain/FavoriteButton row of `components.md` (`on / off` toggle).
/// The two states are visually distinct: filled rose heart when on, outlined
/// ink heart when off — never a colour-only difference, so the state is legible
/// without relying on hue.
///
/// `RefColors.indigo500` (the action anchor) signals the active favourite;
/// the off state uses the ink ramp. Disabled is a null [onChanged]. The hit
/// area meets the 44pt minimum.
class AssenFavoriteButton extends StatelessWidget {
  /// Creates a favourite toggle reflecting [isFavorite].
  ///
  /// [onChanged] receives the requested next value; a null handler disables the
  /// control (e.g. while a mutation is in flight).
  const AssenFavoriteButton({
    required this.isFavorite,
    required this.onChanged,
    super.key,
  });

  /// Whether this cast is currently a favourite (drives the filled heart).
  final bool isFavorite;

  /// Called with the toggled value when tapped. Null disables the control.
  final ValueChanged<bool>? onChanged;

  /// Hit-target floor (Apple HIG / Korean B2C).
  static const double _minTouchTarget = 44;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final enabled = onChanged != null;
    final color = !enabled
        ? colors.neutral300
        : (isFavorite ? colors.indigo500 : colors.ink500);

    return IconButton(
      onPressed: enabled ? () => onChanged!(!isFavorite) : null,
      icon: Icon(isFavorite ? Icons.favorite : Icons.favorite_border),
      iconSize: SpacingTokens.s6,
      color: color,
      disabledColor: colors.neutral300,
      tooltip: isFavorite ? '최애 해제' : '최애 등록',
      constraints: const BoxConstraints(
        minWidth: _minTouchTarget,
        minHeight: _minTouchTarget,
      ),
    );
  }
}
