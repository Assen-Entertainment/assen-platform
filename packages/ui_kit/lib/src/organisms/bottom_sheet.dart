import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/organisms/bottom_cta.dart';

/// A modal bottom sheet shell (`핸들+타이틀+콘텐츠+CTA — 한국 관례 #2`).
///
/// Covers the Containment/BottomSheet row of `components.md` and enforces Korean
/// B2C convention #2 (selection/filter/notice use a bottom sheet, never a
/// dropdown or a desktop dialog). It is the shared chrome — a grab handle, an
/// optional [title], the [child] body and an optional pinned [primaryLabel] CTA
/// — laid on a white surface with a top-rounded corner (`RadiusTokens.xl`).
///
/// Present it with [AssenBottomSheet.show], which wires Material's
/// `showModalBottomSheet` with the Assen barrier and shape so callers never
/// re-specify the chrome.
class AssenBottomSheet extends StatelessWidget {
  /// Creates the sheet body. Prefer [AssenBottomSheet.show] to present it.
  ///
  /// [title] is the optional header. [primaryLabel]/[onPrimary] add a pinned
  /// [AssenBottomCta] (e.g. 적용); omit them for a pure selection sheet that
  /// closes on tap. [child] is the sheet content (a list of options, a filter,
  /// a notice).
  const AssenBottomSheet({
    required this.child,
    this.title,
    this.primaryLabel,
    this.onPrimary,
    super.key,
  });

  /// The sheet content.
  final Widget child;

  /// Optional sheet title.
  final String? title;

  /// Optional pinned CTA label.
  final String? primaryLabel;

  /// The CTA handler; null disables the pinned action.
  final VoidCallback? onPrimary;

  /// Presents [sheet] as an Assen-styled modal bottom sheet.
  ///
  /// Returns the value passed to `Navigator.pop` when the sheet is dismissed.
  /// [isScrollControlled] (default true) lets a tall sheet grow and stay above
  /// the keyboard — required for filter/selection sheets.
  static Future<T?> show<T>(
    BuildContext context, {
    required AssenBottomSheet sheet,
    bool isScrollControlled = true,
  }) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: isScrollControlled,
      backgroundColor: colors.white,
      barrierColor: colors.ink900.withValues(alpha: 0.4),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(RadiusTokens.xl),
        ),
      ),
      builder: (_) => sheet,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return SafeArea(
      top: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Grab handle — the standard affordance signalling a draggable sheet.
          Padding(
            padding: const EdgeInsets.only(
              top: SpacingTokens.s3,
              bottom: SpacingTokens.s2,
            ),
            child: Container(
              width: SpacingTokens.s10,
              height: SpacingTokens.s1,
              decoration: BoxDecoration(
                color: colors.ink200,
                borderRadius: const BorderRadius.all(
                  Radius.circular(RadiusTokens.full),
                ),
              ),
            ),
          ),
          if (title != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                SpacingTokens.screenMargin,
                SpacingTokens.s2,
                SpacingTokens.screenMargin,
                SpacingTokens.s3,
              ),
              child: Text(
                title!,
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
            ),
          Flexible(
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: SpacingTokens.screenMargin,
              ),
              child: child,
            ),
          ),
          if (primaryLabel != null)
            AssenBottomCta(primaryLabel: primaryLabel!, onPrimary: onPrimary),
        ],
      ),
    );
  }
}
