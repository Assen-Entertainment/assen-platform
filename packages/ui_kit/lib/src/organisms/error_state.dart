import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/button.dart';

/// A load-failure placeholder with a retry (`재시도 포함`).
///
/// Covers the Feedback/ErrorState row of `components.md` — the surface shown when
/// a fetch fails (network down, server error). It centres a peach warning glyph
/// over a [title]/[message] and a [retryLabel] button wired to [onRetry]. Peach
/// (not red) keeps a recoverable error calm — red is reserved for destructive
/// confirms and validation (tokens.md §1). The retry is optional so an
/// unrecoverable error can show copy alone.
class AssenErrorState extends StatelessWidget {
  /// Creates an error state with [title] and [message].
  ///
  /// Provide [retryLabel]/[onRetry] to offer a retry CTA (the usual case); omit
  /// both for an unrecoverable error.
  const AssenErrorState({
    required this.title,
    required this.message,
    this.retryLabel = '다시 시도',
    this.onRetry,
    super.key,
  });

  /// The error headline (e.g. "불러오지 못했어요").
  final String title;

  /// The supporting description.
  final String message;

  /// The retry CTA label. Defaults to "다시 시도".
  final String retryLabel;

  /// The retry handler; when null no retry button is shown.
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    // A live region so screen readers announce a load failure when it replaces
    // the in-flight content (title + message are read out on appear).
    return Semantics(
      liveRegion: true,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(SpacingTokens.s8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Peach pastel disc + warning glyph — a recoverable, non-alarming
              // error face (red is for destructive/validation only, tokens.md §1).
              Container(
                width: SpacingTokens.s16,
                height: SpacingTokens.s16,
                decoration: BoxDecoration(
                  color: colors.peachBg,
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Icon(
                  Icons.cloud_off_outlined,
                  size: SpacingTokens.s8,
                  color: colors.peachInk,
                ),
              ),
              const SizedBox(height: SpacingTokens.s6),
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
              if (onRetry != null) ...[
                const SizedBox(height: SpacingTokens.s6),
                AssenButton(
                  label: retryLabel,
                  icon: Icons.refresh,
                  onPressed: onRetry,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
