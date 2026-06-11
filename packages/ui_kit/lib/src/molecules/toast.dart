import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 body.m/label).
const double _toastTextSize = 14; // tokens.md §3 body.m
const double _toastActionSize = 13; // tokens.md §3 label — action

/// Semantic kind of an [AssenToast].
enum AssenToastKind {
  /// 성공 — confirmation (matcha success hue).
  success,

  /// 오류 — failure (red hue).
  error,

  /// 정보 — neutral information. Used for the legally required "정보/광고 수신
  /// 설정이 변경되었습니다" notice when a push toggle changes (Korean B2C
  /// convention #4 / 정보통신망법).
  info,
}

/// A transient toast (`성공 / 오류 / 정보`, optional action).
///
/// Covers the Feedback/Toast row of `components.md`. It is a single pill with a
/// leading status glyph, the message, and an optional trailing text action.
/// The fill is the kind's pastel face and the text/icon its ink (tokens.md §1 —
/// pastel never on text). Show it transiently with [show], which uses the
/// nearest [ScaffoldMessenger]; the widget itself is also directly renderable
/// (and unit-testable) without a messenger.
///
/// A common trigger is Korean B2C convention #4: when a user flips the
/// information/advertising push toggle, surface an [AssenToastKind.info] toast
/// announcing the change (정보통신망법 일시 고지).
class AssenToast extends StatelessWidget {
  /// Creates a toast carrying [message] of the given [kind].
  ///
  /// Provide [actionLabel] + [onAction] for the trailing action (e.g. "실행
  /// 취소"). [icon] overrides the per-kind default glyph.
  const AssenToast({
    required this.message,
    this.kind = AssenToastKind.info,
    this.actionLabel,
    this.onAction,
    this.icon,
    super.key,
  });

  /// The toast text.
  final String message;

  /// Semantic kind — drives the hue. See [AssenToastKind].
  final AssenToastKind kind;

  /// Optional trailing action label. Requires [onAction].
  final String? actionLabel;

  /// Tap handler for the trailing action.
  final VoidCallback? onAction;

  /// Optional leading glyph override.
  final IconData? icon;

  /// Shows [toast] over the nearest [ScaffoldMessenger] as a [SnackBar].
  ///
  /// The toast keeps its own pastel face, so the SnackBar is made transparent.
  /// [duration] defaults to 3 seconds (a comfortable read for a one-line
  /// notice).
  static void show(
    BuildContext context,
    AssenToast toast, {
    Duration duration = const Duration(seconds: 3),
  }) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          content: toast,
          duration: duration,
          backgroundColor: Colors.transparent,
          elevation: 0,
          behavior: SnackBarBehavior.floating,
          padding: EdgeInsets.zero,
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (background, foreground, border, defaultIcon) = _palette(colors);
    final hasAction = actionLabel != null && onAction != null;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        border: Border.all(color: border),
        boxShadow: const [
          BoxShadow(
            color: ElevationTokens.level1Color,
            offset: Offset(
              ElevationTokens.level1OffsetX,
              ElevationTokens.level1OffsetY,
            ),
            blurRadius: ElevationTokens.level1Blur,
          ),
        ],
      ),
      child: Row(
        children: [
          Icon(icon ?? defaultIcon, size: SpacingTokens.s5, color: foreground),
          const SizedBox(width: SpacingTokens.s2),
          Expanded(
            child: Text(
              message,
              style: TextStyle(fontSize: _toastTextSize, color: foreground),
            ),
          ),
          if (hasAction) ...[
            const SizedBox(width: SpacingTokens.s2),
            GestureDetector(
              onTap: onAction,
              child: Text(
                actionLabel!,
                style: TextStyle(
                  fontSize: _toastActionSize,
                  fontWeight: FontWeight.w700,
                  color: foreground,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  (Color, Color, Color, IconData) _palette(AssenColors c) {
    return switch (kind) {
      AssenToastKind.success => (
        c.matchaBgSubtle,
        c.matchaInk,
        c.matchaBorder,
        Icons.check_circle_outline,
      ),
      AssenToastKind.error => (
        c.redBg,
        c.redInk,
        c.redMain,
        Icons.error_outline,
      ),
      AssenToastKind.info => (
        c.skyBgSubtle,
        c.skyInk,
        c.skyBorder,
        Icons.info_outline,
      ),
    };
  }
}
