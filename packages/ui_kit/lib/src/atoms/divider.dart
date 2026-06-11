import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A hairline rule (`풀폭 / 인셋`).
///
/// Covers the Containment/Divider row of `components.md`. Separation is
/// primarily a border job in this system (tokens.md §7), so the divider is a
/// 1px ink-ramp line. [indent]/[endIndent] produce the inset variant used
/// inside list rows so the rule aligns under content rather than the leading
/// edge.
class AssenDivider extends StatelessWidget {
  /// Creates a full-bleed divider.
  ///
  /// Pass [indent]/[endIndent] (typically `SpacingTokens.s4`) for the inset
  /// variant.
  const AssenDivider({this.indent = 0, this.endIndent = 0, super.key});

  /// Leading inset in logical pixels (pass a `SpacingTokens` value).
  final double indent;

  /// Trailing inset in logical pixels.
  final double endIndent;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Divider(
      height: 1,
      thickness: 1,
      indent: indent,
      endIndent: endIndent,
      color: colors.ink100,
    );
  }
}
