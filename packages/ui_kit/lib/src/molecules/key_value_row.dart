import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A label–value row (`기본 / 강조`).
///
/// Covers the Containment/KeyValueRow row of `components.md` — reservation
/// detail and POS summary lines. The [label] sits on the leading edge in
/// secondary ink and the [value] is trailing-aligned. The [emphasis] variant
/// (e.g. a total amount) renders the value larger in the indigo ink so the key
/// figure stands out without changing layout.
class AssenKeyValueRow extends StatelessWidget {
  /// Creates a row pairing [label] with [value].
  ///
  /// Set [emphasis] true for the highlighted variant (larger, indigo value),
  /// typically the final/total line in a summary.
  const AssenKeyValueRow({
    required this.label,
    required this.value,
    this.emphasis = false,
    super.key,
  });

  /// The leading label (e.g. "결제 금액").
  final String label;

  /// The trailing value (e.g. "₩12,000").
  final String value;

  /// Whether to render the emphasised (강조) value styling.
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink600,
            ),
          ),
          const SizedBox(width: SpacingTokens.s4),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: emphasis
                    ? TypographyTokens.titleMSize
                    : TypographyTokens.bodyMSize,
                fontWeight: emphasis ? FontWeight.w700 : FontWeight.w500,
                color: emphasis ? colors.indigoText : colors.ink900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
