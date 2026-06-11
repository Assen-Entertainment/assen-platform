/// Placeholder spacing scale mirroring `docs/design/tokens.json` `spacing.*`.
///
/// The base unit is 4 logical pixels; named steps below are the subset already
/// fixed in the token source. P1 regenerates this from the DTCG file, at which
/// point this hand-written class is deleted.
class SpacingTokens {
  const SpacingTokens._();

  /// Base grid unit in logical pixels. All steps are multiples of this.
  static const double base = 4;

  /// Returns the spacing value, in logical pixels, for a [step] on the grid.
  ///
  /// A [step] of 4 yields 16px, matching the `spacing.4` token. Throws
  /// [ArgumentError] for a negative [step] because spacing is never negative.
  static double ofStep(int step) {
    if (step < 0) {
      throw ArgumentError.value(step, 'step', 'must be non-negative');
    }
    return base * step;
  }
}
