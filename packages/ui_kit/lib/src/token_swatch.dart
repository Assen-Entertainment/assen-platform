import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A minimal colour swatch chip proving the design-token pipeline renders.
///
/// It consumes a generated [RefColors] value (via [color]) plus the generated
/// [RadiusTokens]/[SpacingTokens] scales, so a widget test over it exercises
/// the full path tokens.json -> Style Dictionary -> Dart -> Flutter (ASS-128).
/// This is intentionally tiny; the real widget catalogue arrives in ASS-88.
class TokenSwatch extends StatelessWidget {
  /// Creates a swatch filling itself with [color] and labelling it [label].
  const TokenSwatch({required this.color, required this.label, super.key});

  /// The fill colour — pass a generated [RefColors] primitive.
  final Color color;

  /// The text label shown beneath the swatch (e.g. the token name).
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: SpacingTokens.s16,
          height: SpacingTokens.s16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(RadiusTokens.md),
            border: Border.all(color: RefColors.ink200),
          ),
        ),
        const SizedBox(height: SpacingTokens.s2),
        Text(label, style: TypographyTokens.captionMicro),
      ],
    );
  }
}
