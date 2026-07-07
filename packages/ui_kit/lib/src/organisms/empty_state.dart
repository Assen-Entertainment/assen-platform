import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/button.dart';

/// An empty-collection placeholder (`문구만 / +CTA`).
///
/// Covers the Feedback/EmptyState row of `components.md` — the "빈 앨범 / 예약 없음 /
/// 쿠폰 없음" surface that replaces an empty list (screens.md: every list's empty
/// case is this component, not a separate screen). It centres an illustration
/// [slot] (a pastel motif, never a grey box — screens.md 밀도 규칙) over a [title]
/// and [message], with an optional [actionLabel] CTA to recover (e.g. 캐스트 보러
/// 가기). Omit the action for a purely informational empty state.
class AssenEmptyState extends StatelessWidget {
  /// Creates an empty state with [title] and [message].
  ///
  /// [slot] is the illustration/motif widget (sized by the caller). Provide
  /// [actionLabel]/[onAction] to offer a recovery CTA; omit both for a
  /// copy-only empty state.
  const AssenEmptyState({
    required this.title,
    required this.message,
    this.slot,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  /// Optional illustration/motif widget shown above the copy.
  final Widget? slot;

  /// The empty-state headline (e.g. "아직 모은 체키가 없어요").
  final String title;

  /// The supporting description.
  final String message;

  /// Optional recovery CTA label; when set an [AssenButton] is shown.
  final String? actionLabel;

  /// The CTA handler.
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    // A live region so screen readers announce the empty state when it replaces
    // the in-flight content (title + message are read out on appear).
    return Semantics(
      liveRegion: true,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(SpacingTokens.s8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (slot != null) ...[
                slot!,
                const SizedBox(height: SpacingTokens.s6),
              ],
              Text(
                title,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                message,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  height: 1.5,
                  color: colors.ink700,
                ),
              ),
              if (actionLabel != null) ...[
                const SizedBox(height: SpacingTokens.s6),
                AssenButton(label: actionLabel!, onPressed: onAction),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
