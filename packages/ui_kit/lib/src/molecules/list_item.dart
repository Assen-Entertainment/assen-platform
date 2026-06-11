import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 title.m/body.s).
const double _listTitleSize = 16; // tokens.md §3 title.m
const double _listSubtitleSize = 12; // tokens.md §3 body.s

/// A general-purpose list row with `leading / title / subtitle / trailing`
/// slots.
///
/// Covers the Containment/ListItem row of `components.md`. It is the workhorse
/// row used across settings, menus and detail lists. The slots are plain
/// widgets so callers compose atoms into them (e.g. an avatar leading, a status
/// badge trailing). When [onTap] is set and no [trailing] is given, a chevron
/// is shown so the row reads as navigable (the common case).
///
/// Touch target: the row is pinned to a 44pt minimum height (Korean B2C / HIG).
class AssenListItem extends StatelessWidget {
  /// Creates a list row titled [title].
  ///
  /// [leading]/[trailing] are optional slot widgets; [subtitle] is secondary
  /// text under the title. [onTap] makes the whole row tappable (and shows a
  /// chevron when [trailing] is omitted and [showChevron] is true).
  const AssenListItem({
    required this.title,
    this.subtitle,
    this.leading,
    this.trailing,
    this.onTap,
    this.showChevron = true,
    super.key,
  });

  /// The primary row text.
  final String title;

  /// Optional secondary text under [title].
  final String? subtitle;

  /// Optional leading slot (icon, avatar, …).
  final Widget? leading;

  /// Optional trailing slot (badge, value, switch, …). Suppresses the auto
  /// chevron when provided.
  final Widget? trailing;

  /// Tap handler; when set the whole row is tappable.
  final VoidCallback? onTap;

  /// Whether to show the navigation chevron when [onTap] is set and there is no
  /// [trailing]. Defaults to true.
  final bool showChevron;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    final effectiveTrailing =
        trailing ??
        (onTap != null && showChevron
            ? Icon(Icons.chevron_right, color: colors.ink500)
            : null);

    final row = Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      child: Row(
        children: [
          if (leading != null) ...[
            leading!,
            const SizedBox(width: SpacingTokens.s3),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: _listTitleSize,
                    fontWeight: FontWeight.w600,
                    color: colors.ink900,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: SpacingTokens.s1),
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: _listSubtitleSize,
                      color: colors.ink700,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (effectiveTrailing != null) ...[
            const SizedBox(width: SpacingTokens.s3),
            effectiveTrailing,
          ],
        ],
      ),
    );

    final constrained = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 44),
      child: row,
    );

    if (onTap == null) return constrained;
    return Material(
      type: MaterialType.transparency,
      child: InkWell(onTap: onTap, child: constrained),
    );
  }
}
