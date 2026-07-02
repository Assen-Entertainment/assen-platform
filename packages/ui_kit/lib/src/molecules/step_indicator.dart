import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A linear step-progress indicator for multi-step flows.
///
/// Covers the Navigation/StepIndicator row of `components.md` — the signup and
/// reservation flows, and specifically the Korean identity-verification flow
/// (약관 → 통신사 → 번호 → OTP → 완료, convention #5). Renders [count] nodes joined
/// by connectors: completed nodes are filled rose with a check, the current
/// node is an outlined rose ring, and upcoming nodes are muted ink dots. The
/// progression reads by fill and shape, never by colour alone.
class AssenStepIndicator extends StatelessWidget {
  /// Creates an indicator with [count] steps and [currentStep] active
  /// (zero-based; steps before it are treated as completed).
  ///
  /// Optional [labels] (one per step) are shown under the nodes.
  const AssenStepIndicator({
    required this.count,
    required this.currentStep,
    this.labels,
    super.key,
  }) : assert(
         labels == null || labels.length == count,
         'labels, when given, must have one entry per step',
       );

  /// Total number of steps.
  final int count;

  /// Zero-based index of the active step. Earlier steps are completed.
  final int currentStep;

  /// Optional per-step captions.
  final List<String>? labels;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < count; i++) ...[
          _Node(
            state: _stateOf(i),
            index: i,
            label: labels?[i],
            colors: colors,
          ),
          if (i < count - 1)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: SpacingTokens.s3),
                child: Container(
                  height: 2,
                  color: i < currentStep ? colors.roseMain : colors.ink200,
                ),
              ),
            ),
        ],
      ],
    );
  }

  _StepState _stateOf(int i) {
    if (i < currentStep) return _StepState.complete;
    if (i == currentStep) return _StepState.current;
    return _StepState.upcoming;
  }
}

enum _StepState { complete, current, upcoming }

/// One step node plus its optional caption.
class _Node extends StatelessWidget {
  const _Node({
    required this.state,
    required this.index,
    required this.label,
    required this.colors,
  });

  final _StepState state;
  final int index;
  final String? label;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    final Widget dot;
    switch (state) {
      case _StepState.complete:
        dot = Container(
          width: SpacingTokens.s6,
          height: SpacingTokens.s6,
          decoration: BoxDecoration(
            color: colors.roseMain,
            shape: BoxShape.circle,
          ),
          child: Icon(Icons.check, size: SpacingTokens.s4, color: colors.white),
        );
      case _StepState.current:
        dot = Container(
          width: SpacingTokens.s6,
          height: SpacingTokens.s6,
          decoration: BoxDecoration(
            color: colors.white,
            shape: BoxShape.circle,
            border: Border.all(color: colors.roseMain, width: 2),
          ),
          alignment: Alignment.center,
          child: Text(
            '${index + 1}',
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              fontWeight: FontWeight.w700,
              color: colors.roseMain,
            ),
          ),
        );
      case _StepState.upcoming:
        dot = Container(
          width: SpacingTokens.s6,
          height: SpacingTokens.s6,
          decoration: BoxDecoration(
            color: colors.ink100,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Text(
            '${index + 1}',
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              fontWeight: FontWeight.w600,
              color: colors.ink500,
            ),
          ),
        );
    }

    if (label == null) return dot;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        dot,
        const SizedBox(height: SpacingTokens.s1),
        SizedBox(
          width: SpacingTokens.s16,
          child: Text(
            label!,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              color: state == _StepState.upcoming
                  ? colors.ink500
                  : colors.ink900,
            ),
          ),
        ),
      ],
    );
  }
}
