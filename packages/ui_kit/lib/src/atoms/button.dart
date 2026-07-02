import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Visual emphasis of an [AssenButton].
///
/// Why an enum (not booleans): variants are a closed set in the design system
/// (`components.md` Actions), so an enum makes illegal combinations
/// unrepresentable and keeps call sites self-documenting.
enum AssenButtonStyle {
  /// Solid rose fill — the single primary action per screen (Korean B2C
  /// convention #1: one main action, usually the bottom CTA). Uses the only
  /// solid action colour in the palette (`RefColors.roseMain`).
  primary,

  /// Tonal strawberry fill for secondary actions that still need presence but
  /// must not compete with [primary]. Pastel surface + strawberry ink text
  /// (pastels are background-only; text uses the hue's ink step —
  /// tokens.md §1).
  secondary,

  /// Text-only action for the lowest-emphasis / tertiary case. No fill, ink
  /// label, used inline (e.g. "취소", "전체보기").
  ghost,
}

/// The design-system button.
///
/// Covers the Actions/Button row of `components.md` with `style` driving the
/// three visual variants and the framework's [ButtonStyle] handling the
/// `default / pressed / disabled` states (mobile has no hover). Disabled is
/// expressed by passing a null [onPressed].
///
/// Touch target: the minimum size is pinned to 44×44 logical pixels (Korean
/// B2C / Apple HIG minimum) regardless of label length, so even short labels
/// stay comfortably tappable.
///
/// Colour, radius and spacing come exclusively from tokens — never hard-code a
/// hex or inset here (tokens.md). Gradients are forbidden; every fill is solid.
class AssenButton extends StatelessWidget {
  /// Creates a button rendered with [style] (defaults to
  /// [AssenButtonStyle.primary]).
  ///
  /// A null [onPressed] renders the disabled state. [label] is the button text;
  /// [icon] optionally precedes it (e.g. a leading glyph on a CTA).
  const AssenButton({
    required this.label,
    required this.onPressed,
    this.style = AssenButtonStyle.primary,
    this.icon,
    this.expand = false,
    super.key,
  });

  /// The button text. Kept as a plain [String] (not a child) because every
  /// button in the system is a single label styled by the theme.
  final String label;

  /// Tap handler. When null the button is disabled (greyed, non-interactive).
  final VoidCallback? onPressed;

  /// Visual emphasis — see [AssenButtonStyle].
  final AssenButtonStyle style;

  /// Optional leading icon shown before [label].
  final IconData? icon;

  /// When true the button stretches to its parent's full width — used for the
  /// bottom CTA (Korean B2C convention #1). Defaults to intrinsic width.
  final bool expand;

  /// Minimum tappable height/width (Apple HIG / Korean B2C). 44 is an
  /// accessibility floor, not a spacing token, so it is a named constant rather
  /// than a `SpacingTokens` value of the wrong semantic.
  static const double _minTouchTarget = 44;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final child = _ButtonLabel(label: label, icon: icon);

    final Widget button = switch (style) {
      AssenButtonStyle.primary => FilledButton(
        onPressed: onPressed,
        style: _primaryStyle(colors),
        child: child,
      ),
      AssenButtonStyle.secondary => FilledButton(
        onPressed: onPressed,
        style: _secondaryStyle(colors),
        child: child,
      ),
      AssenButtonStyle.ghost => TextButton(
        onPressed: onPressed,
        style: _ghostStyle(colors),
        child: child,
      ),
    };

    return SizedBox(width: expand ? double.infinity : null, child: button);
  }

  ButtonStyle _primaryStyle(AssenColors colors) {
    return FilledButton.styleFrom(
      backgroundColor: colors.roseMain,
      foregroundColor: colors.white,
      disabledBackgroundColor: colors.ink100,
      disabledForegroundColor: colors.ink500,
      minimumSize: const Size(_minTouchTarget, _minTouchTarget),
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s5,
        vertical: SpacingTokens.s3,
      ),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.md)),
      ),
      textStyle: _textStyle,
    );
  }

  ButtonStyle _secondaryStyle(AssenColors colors) {
    return FilledButton.styleFrom(
      backgroundColor: colors.strawberryBg,
      foregroundColor: colors.strawberryInk,
      disabledBackgroundColor: colors.ink100,
      disabledForegroundColor: colors.ink500,
      minimumSize: const Size(_minTouchTarget, _minTouchTarget),
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s5,
        vertical: SpacingTokens.s3,
      ),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.md)),
      ),
      textStyle: _textStyle,
    );
  }

  ButtonStyle _ghostStyle(AssenColors colors) {
    return TextButton.styleFrom(
      foregroundColor: colors.strawberryInk,
      disabledForegroundColor: colors.ink500,
      minimumSize: const Size(_minTouchTarget, _minTouchTarget),
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.md)),
      ),
      textStyle: _textStyle,
    );
  }

  // CTA 버튼은 본문보다 또렷해야 하므로 body.l(16)을 쓴다.
  static const TextStyle _textStyle = TextStyle(
    fontSize: TypographyTokens.bodyLSize,
    fontWeight: FontWeight.w600,
    height: 1.2,
  );
}

/// Internal row laying out the optional [icon] before [label].
class _ButtonLabel extends StatelessWidget {
  const _ButtonLabel({required this.label, this.icon});

  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final text = Text(label);
    if (icon == null) return text;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: SpacingTokens.s5),
        const SizedBox(width: SpacingTokens.s2),
        text,
      ],
    );
  }
}
