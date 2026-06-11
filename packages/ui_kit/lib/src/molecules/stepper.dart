import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 title.m=16).
const double _stepperValueSize = 16; // tokens.md §3 title.m — the count

/// A numeric stepper (`default / min / max`).
///
/// Covers the Inputs/Stepper row of `components.md` — reservation party size.
/// Composes two [AssenIconButton]s (−/+) around a live count. The decrement is
/// disabled at [min] and the increment at [max] (the `min`/`max` variants), so
/// the value can never leave `[min, max]`. Colours come from the ink ramp; the
/// buttons inherit the atom's 44pt touch target.
class AssenStepper extends StatelessWidget {
  /// Creates a stepper showing [value].
  ///
  /// [onChanged] receives the next value, already clamped to `[min, max]`; null
  /// disables the whole control. [min] defaults to 1 (a party of at least one).
  const AssenStepper({
    required this.value,
    required this.onChanged,
    this.min = 1,
    this.max = 99,
    this.semanticLabel = '수량',
    super.key,
  });

  /// The current count.
  final int value;

  /// Called with the next (clamped) value. Null disables the control.
  final ValueChanged<int>? onChanged;

  /// Smallest allowed value — decrement is disabled here.
  final int min;

  /// Largest allowed value — increment is disabled here.
  final int max;

  /// Accessibility label describing what is being counted (e.g. "인원").
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final enabled = onChanged != null;
    final canDecrement = enabled && value > min;
    final canIncrement = enabled && value < max;

    return Semantics(
      label: semanticLabel,
      value: '$value',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AssenIconButton(
            icon: Icons.remove,
            semanticLabel: '$semanticLabel 줄이기',
            onPressed: canDecrement ? () => onChanged!(value - 1) : null,
          ),
          Container(
            constraints: const BoxConstraints(minWidth: SpacingTokens.s10),
            alignment: Alignment.center,
            child: Text(
              '$value',
              style: TextStyle(
                fontSize: _stepperValueSize,
                fontWeight: FontWeight.w700,
                color: enabled ? colors.ink900 : colors.ink500,
              ),
            ),
          ),
          AssenIconButton(
            icon: Icons.add,
            semanticLabel: '$semanticLabel 늘리기',
            onPressed: canIncrement ? () => onChanged!(value + 1) : null,
          ),
        ],
      ),
    );
  }
}
