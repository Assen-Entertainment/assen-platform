import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Severity of an [AssenNoticeBar].
enum AssenNoticeKind {
  /// info — neutral notice (sky pastel face).
  info,

  /// warning — caution that still isn't an error (lemon pastel face).
  warning,
}

/// An inline notice strip (`info / warning`).
///
/// Covers the Containment/NoticeBar row of `components.md` — a 공지 띠 sitting in
/// the content flow. It is a pastel *face* (tokens.md §1: pastel is fill-only)
/// carrying a leading glyph and a message in the hue's ink, so the colour reads
/// the severity without ever putting pastel on text. A `border` step separates
/// it from adjacent pastel surfaces (tokens.md §2). Not a transient toast —
/// this stays in layout.
class AssenNoticeBar extends StatelessWidget {
  /// Creates a notice strip carrying [message] at the given [kind].
  ///
  /// Optionally override the leading [icon]; otherwise a sensible default per
  /// [kind] is used.
  const AssenNoticeBar({
    required this.message,
    this.kind = AssenNoticeKind.info,
    this.icon,
    super.key,
  });

  /// The notice text.
  final String message;

  /// Severity — drives the pastel hue. See [AssenNoticeKind].
  final AssenNoticeKind kind;

  /// Optional leading glyph override.
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (background, foreground, border, defaultIcon) = _palette(colors);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        border: Border.all(color: border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon ?? defaultIcon, size: SpacingTokens.s5, color: foreground),
          const SizedBox(width: SpacingTokens.s2),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                color: foreground,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  (Color, Color, Color, IconData) _palette(AssenColors c) {
    return switch (kind) {
      AssenNoticeKind.info => (
        c.skyBgSubtle,
        c.skyInk,
        c.skyBorder,
        Icons.info_outline,
      ),
      AssenNoticeKind.warning => (
        c.lemonBgSubtle,
        c.lemonInk,
        c.lemonBorder,
        Icons.warning_amber_outlined,
      ),
    };
  }
}
