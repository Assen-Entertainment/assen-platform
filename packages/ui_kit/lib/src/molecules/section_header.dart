import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3 headline/label).
const double _sectionTitleSize = 19; // tokens.md §3 title.l — section title
const double _sectionActionSize = 13; // tokens.md §3 label — "전체보기 ›"

/// A section heading with an optional trailing action (`액션 유/무`).
///
/// Covers the Navigation/SectionHeader row of `components.md`. It introduces a
/// content block with a bold [title] and, optionally, a trailing text action
/// ("전체보기 ›") wired to [onAction]. The chevron is part of the action affordance
/// so it only appears when the action does. Used above home carousels and list
/// groups.
class AssenSectionHeader extends StatelessWidget {
  /// Creates a section header titled [title].
  ///
  /// Provide [actionLabel] + [onAction] for the trailing action variant; omit
  /// both for the title-only variant.
  const AssenSectionHeader({
    required this.title,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  /// The section title.
  final String title;

  /// Optional trailing action label (e.g. "전체보기"). Requires [onAction].
  final String? actionLabel;

  /// Tap handler for the trailing action.
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final hasAction = actionLabel != null && onAction != null;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: TextStyle(
                fontSize: _sectionTitleSize,
                fontWeight: FontWeight.w700,
                color: colors.ink900,
              ),
            ),
          ),
          if (hasAction)
            InkWell(
              onTap: onAction,
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.sm),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.s2,
                  vertical: SpacingTokens.s1,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      actionLabel!,
                      style: TextStyle(
                        fontSize: _sectionActionSize,
                        fontWeight: FontWeight.w600,
                        color: colors.ink700,
                      ),
                    ),
                    Icon(
                      Icons.chevron_right,
                      size: SpacingTokens.s4,
                      color: colors.ink500,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
