import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/button.dart';

/// The bottom-fixed call-to-action bar (`단일/2분할 — 한국 관례 #1`).
///
/// Covers the Actions/BottomCTA row of `components.md` and enforces Korean B2C
/// convention #1 (`tokens.md`/components.md §관례): exactly one primary action
/// per screen, pinned to the bottom and lifted above the keyboard. It composes
/// [AssenButton]s on a white bar with a hairline top border, and uses
/// [SafeArea] + `viewInsets` so it rides the keyboard during entry flows.
///
/// Use the default constructor for the single-action case ([primaryLabel]); use
/// [AssenBottomCta.split] for the two-action layout (a ghost/secondary on the
/// left, the primary on the right — e.g. 이전/다음, 취소/삭제).
class AssenBottomCta extends StatelessWidget {
  /// Creates a single full-width primary CTA.
  ///
  /// [onPrimary] null disables the button (e.g. an incomplete form). [primary]
  /// chooses the emphasis (defaults to the rose primary).
  const AssenBottomCta({
    required this.primaryLabel,
    required this.onPrimary,
    this.primary = AssenButtonStyle.primary,
    super.key,
  }) : secondaryLabel = null,
       onSecondary = null,
       secondary = AssenButtonStyle.ghost;

  /// Creates a two-action bar: [secondaryLabel] on the left, [primaryLabel] on
  /// the right.
  ///
  /// The split is one-third / two-thirds so the primary keeps visual weight. The
  /// secondary defaults to a ghost action (e.g. 이전); pass [secondary] to make
  /// it tonal instead.
  const AssenBottomCta.split({
    required this.primaryLabel,
    required this.onPrimary,
    required this.secondaryLabel,
    required this.onSecondary,
    this.primary = AssenButtonStyle.primary,
    this.secondary = AssenButtonStyle.ghost,
    super.key,
  });

  /// The primary action label.
  final String primaryLabel;

  /// The primary handler; null disables the action.
  final VoidCallback? onPrimary;

  /// The primary button emphasis.
  final AssenButtonStyle primary;

  /// The secondary action label (split layout only).
  final String? secondaryLabel;

  /// The secondary handler (split layout only).
  final VoidCallback? onSecondary;

  /// The secondary button emphasis (split layout only).
  final AssenButtonStyle secondary;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isSplit = secondaryLabel != null;

    final row = isSplit
        ? Row(
            children: [
              Expanded(
                child: AssenButton(
                  label: secondaryLabel!,
                  style: secondary,
                  onPressed: onSecondary,
                  expand: true,
                ),
              ),
              const SizedBox(width: SpacingTokens.s3),
              Expanded(
                flex: 2,
                child: AssenButton(
                  label: primaryLabel,
                  style: primary,
                  onPressed: onPrimary,
                  expand: true,
                ),
              ),
            ],
          )
        : AssenButton(
            label: primaryLabel,
            style: primary,
            onPressed: onPrimary,
            expand: true,
          );

    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.white,
        border: Border(top: BorderSide(color: colors.ink100)),
      ),
      // SafeArea keeps the bar clear of the home indicator; the viewInsets
      // padding (added by Scaffold via MediaQuery) lifts it above the keyboard.
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s3,
            SpacingTokens.screenMargin,
            SpacingTokens.s3,
          ),
          child: row,
        ),
      ),
    );
  }
}
