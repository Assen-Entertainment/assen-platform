import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A bare, single-glyph tappable action.
///
/// Covers the Actions/IconButton row of `components.md`
/// (`default / pressed / disabled`, mobile — no hover). Used for app-bar
/// actions, close buttons, and inline controls where a label would be noise.
///
/// The hit area is pinned to a 48×48 logical-pixel minimum (Material
/// accessibility; also clears the 44pt Apple HIG / Korean B2C floor) even when
/// the glyph is small. Disabled is expressed with a null [onPressed]. Colours
/// come from the ink ramp via tokens — never hard-coded.
class AssenIconButton extends StatelessWidget {
  /// Creates an icon button showing [icon].
  ///
  /// A null [onPressed] renders the disabled state. [semanticLabel] is required
  /// because an icon-only control is invisible to screen readers otherwise.
  const AssenIconButton({
    required this.icon,
    required this.onPressed,
    required this.semanticLabel,
    this.color,
    super.key,
  });

  /// The glyph to render.
  final IconData icon;

  /// Tap handler. When null the button is disabled (faded, non-interactive).
  final VoidCallback? onPressed;

  /// Accessibility label announced by screen readers (e.g. "닫기").
  final String semanticLabel;

  /// Optional override for the glyph colour. Defaults to [AssenColors.ink900]
  /// (primary on-surface ink). Pass a hue's ink step for tinted actions.
  final Color? color;

  /// Hit-target floor (Material 48dp; also clears the 44pt Apple HIG / Korean
  /// B2C floor). Not a spacing token — it is an accessibility minimum, so it is
  /// a named constant.
  static const double _minTouchTarget = 48;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return IconButton(
      onPressed: onPressed,
      icon: Icon(icon),
      iconSize: SpacingTokens.s6,
      color: color ?? colors.ink900,
      disabledColor: colors.neutral300,
      tooltip: semanticLabel,
      constraints: const BoxConstraints(
        minWidth: _minTouchTarget,
        minHeight: _minTouchTarget,
      ),
    );
  }
}
