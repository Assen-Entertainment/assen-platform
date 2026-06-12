import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/button.dart';

/// A centred confirm/cancel dialog (`1버튼/2버튼(파괴적=red)`).
///
/// Covers the Containment/Dialog row of `components.md`. Used sparingly — Korean
/// B2C convention #2 routes most choices to a bottom sheet — this is the
/// blocking confirm for a single decision (e.g. 예약을 취소할까요?). It is a white
/// card (`RadiusTokens.xl`) holding a [title], an optional [message] and one or
/// two [AssenButton] actions. A [destructive] confirm swaps the primary to the
/// error rose so irreversible actions read as such (tokens.md §1 — colour plus
/// label, never colour alone).
///
/// Present it with [AssenDialog.show].
class AssenDialog extends StatelessWidget {
  /// Creates a dialog. Prefer [AssenDialog.show] to present it.
  ///
  /// [confirmLabel]/[onConfirm] are the primary action. [cancelLabel]/[onCancel]
  /// add the secondary (ghost) action for the two-button case; omit them for a
  /// single-button acknowledgement. [destructive] tints the confirm red.
  const AssenDialog({
    required this.title,
    required this.confirmLabel,
    required this.onConfirm,
    this.message,
    this.cancelLabel,
    this.onCancel,
    this.destructive = false,
    super.key,
  });

  /// The dialog title.
  final String title;

  /// Optional supporting message.
  final String? message;

  /// The confirm (primary) action label.
  final String confirmLabel;

  /// The confirm handler.
  final VoidCallback? onConfirm;

  /// Optional cancel action label; when set the dialog shows two buttons.
  final String? cancelLabel;

  /// The cancel handler.
  final VoidCallback? onCancel;

  /// Whether the confirm is a destructive/irreversible action (error rose).
  final bool destructive;

  /// Presents [dialog] as an Assen-styled modal dialog.
  ///
  /// Returns the value passed to `Navigator.pop`. The barrier uses the ink
  /// scrim; the dialog is dismissible by tapping outside.
  static Future<T?> show<T>(
    BuildContext context, {
    required AssenDialog dialog,
  }) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return showDialog<T>(
      context: context,
      barrierColor: colors.ink900.withValues(alpha: 0.4),
      builder: (_) => dialog,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final hasCancel = cancelLabel != null;

    final confirmButton = AssenButton(
      label: confirmLabel,
      onPressed: onConfirm,
      expand: true,
    );
    // Destructive confirms wear the error rose. Overriding the AssenColors
    // extension's action anchor (roseMain) in this subtree recolours the
    // primary AssenButton without a new style enum (single use; tokens.md §1 —
    // irreversible actions also carry the cancel label, never colour alone).
    final confirm = destructive
        ? Theme(
            data: Theme.of(context).copyWith(
              extensions: [colors.copyWith(roseMain: colors.redMain)],
            ),
            child: confirmButton,
          )
        : confirmButton;

    return Dialog(
      backgroundColor: colors.white,
      surfaceTintColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s8,
      ),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.xl)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(SpacingTokens.s5),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w700,
                color: colors.ink900,
              ),
            ),
            if (message != null) ...[
              const SizedBox(height: SpacingTokens.s2),
              Text(
                message!,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  height: 1.5,
                  color: colors.ink700,
                ),
              ),
            ],
            const SizedBox(height: SpacingTokens.s5),
            if (hasCancel)
              Row(
                children: [
                  Expanded(
                    child: AssenButton(
                      label: cancelLabel!,
                      style: AssenButtonStyle.ghost,
                      onPressed: onCancel,
                      expand: true,
                    ),
                  ),
                  const SizedBox(width: SpacingTokens.s3),
                  Expanded(child: confirm),
                ],
              )
            else
              confirm,
          ],
        ),
      ),
    );
  }
}
