import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/layout/adaptive_shell.dart';
import 'package:ui_kit/src/layout/window_size.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';

/// Desktop-first app shell: a persistent sidebar at large/XL widths.
///
/// This is the web/desktop peer of [AssenAdaptiveShell]. Below the large window
/// size class it delegates to [AssenAdaptiveShell] verbatim, so compact (bottom
/// tab bar), medium (collapsed rail), and expanded (extended rail + reading
/// column) are byte-for-byte the existing behaviour. At
/// [AssenWindowSize.large] and wider it replaces the rail with a fixed
/// [AssenLayout.sidebarWidth] sidebar and lets the body fill the remaining
/// width (no reading-column cap), so desktop surfaces can lay out as canonical
/// (feed / supporting-pane / list-detail) layouts.
///
/// The destination model is the same [AssenTabItem] list used everywhere, so
/// navigation semantics never change with width.
class AssenSidebarShell extends StatelessWidget {
  /// Creates a sidebar shell around [body].
  const AssenSidebarShell({
    required this.currentIndex,
    required this.onChanged,
    required this.items,
    required this.body,
    this.header,
    super.key,
  }) : assert(items.length >= 2, 'A sidebar shell needs two destinations');

  /// The selected destination index shared by sidebar, rail and bottom nav.
  final int currentIndex;

  /// Called when a destination is selected.
  final ValueChanged<int> onChanged;

  /// The ordered navigation destinations rendered at every window size.
  final List<AssenTabItem> items;

  /// The active route subtree managed by the app router.
  final Widget body;

  /// Optional brand/header slot pinned above the destinations (large/XL only).
  final Widget? header;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return LayoutBuilder(
      builder: (context, constraints) {
        final size = AssenWindowSize.fromWidth(constraints.maxWidth);
        if (!size.atLeast(AssenWindowSize.large)) {
          // Compact / medium / expanded keep the existing adaptive shell.
          return AssenAdaptiveShell(
            currentIndex: currentIndex,
            onChanged: onChanged,
            items: items,
            body: body,
          );
        }

        // Large / extra-large: persistent desktop sidebar + full-width body.
        return Scaffold(
          backgroundColor: colors.white,
          body: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Sidebar(
                items: items,
                currentIndex: currentIndex,
                onChanged: onChanged,
                header: header,
              ),
              Expanded(child: body),
            ],
          ),
        );
      },
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.items,
    required this.currentIndex,
    required this.onChanged,
    required this.header,
  });

  final List<AssenTabItem> items;
  final int currentIndex;
  final ValueChanged<int> onChanged;
  final Widget? header;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Container(
      key: const Key('assenDesktopSidebar'),
      width: AssenLayout.sidebarWidth,
      decoration: BoxDecoration(
        color: colors.neutral100,
        border: Border(right: BorderSide(color: colors.neutral100)),
      ),
      child: SafeArea(
        right: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (header != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  SpacingTokens.s5,
                  SpacingTokens.s5,
                  SpacingTokens.s5,
                  SpacingTokens.s4,
                ),
                child: header,
              ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.s3,
                  vertical: SpacingTokens.s2,
                ),
                children: [
                  for (var i = 0; i < items.length; i++)
                    _SidebarDestination(
                      item: items[i],
                      selected: i == currentIndex,
                      onTap: () => onChanged(i),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SidebarDestination extends StatelessWidget {
  const _SidebarDestination({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final AssenTabItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final foreground = selected ? colors.indigoText : colors.ink600;
    final glyph = Icon(
      selected ? item.activeIcon : item.icon,
      color: selected ? colors.indigoText : colors.ink500,
      size: SpacingTokens.s6,
    );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s1),
      child: Material(
        color: selected ? colors.indigo100 : Colors.transparent,
        borderRadius: BorderRadius.circular(RadiusTokens.md),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(RadiusTokens.md),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: SpacingTokens.s3,
              vertical: SpacingTokens.s3,
            ),
            child: Row(
              children: [
                if (item.badgeCount > 0)
                  Stack(
                    clipBehavior: Clip.none,
                    children: [
                      glyph,
                      Positioned(
                        right: -SpacingTokens.s2,
                        top: -SpacingTokens.s1,
                        child: AssenCountBadge(count: item.badgeCount),
                      ),
                    ],
                  )
                else
                  glyph,
                const SizedBox(width: SpacingTokens.s3),
                Expanded(
                  child: Text(
                    item.label,
                    style: TypographyTokens.bodyM.copyWith(
                      color: foreground,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
