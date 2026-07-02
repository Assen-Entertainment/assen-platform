import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/layout/content_column.dart';
import 'package:ui_kit/src/layout/window_size.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';

/// Adaptive application shell for the fan app's fixed destination set.
///
/// The destination model stays identical at every width; only the navigation
/// chrome moves according to Material 3 window size classes. Compact preserves
/// the existing [AssenTabBar] bottom navigation path for mobile behaviour,
/// medium switches to a collapsed [NavigationRail], and expanded extends the
/// rail while placing the body in [AssenContentColumn].
class AssenAdaptiveShell extends StatelessWidget {
  /// Creates an adaptive shell around [body].
  ///
  /// [items] should be the same ordered destinations used by the compact tab
  /// bar so browser/tablet width changes never alter navigation semantics.
  const AssenAdaptiveShell({
    required this.currentIndex,
    required this.onChanged,
    required this.items,
    required this.body,
    this.contentMaxWidth = AssenLayout.contentMaxWidth,
    super.key,
  }) : assert(items.length >= 2, 'An adaptive shell needs two destinations');

  /// The selected destination index shared by rail and bottom navigation.
  final int currentIndex;

  /// Called when a destination is selected.
  final ValueChanged<int> onChanged;

  /// The ordered navigation destinations rendered at every window size.
  final List<AssenTabItem> items;

  /// The active route subtree managed by the app router.
  final Widget body;

  /// Maximum body width at the expanded size class (centered beyond it).
  ///
  /// Defaults to the fan reading column; the operator console passes the wider
  /// [AssenLayout.consoleContentMaxWidth].
  final double contentMaxWidth;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final selectedRailLabelStyle = TypographyTokens.captionMicro.copyWith(
      color: colors.roseMain,
    );
    final unselectedRailLabelStyle = TypographyTokens.captionMicro.copyWith(
      color: colors.ink500,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final size = AssenWindowSize.fromWidth(constraints.maxWidth);
        if (size == AssenWindowSize.compact) {
          return Scaffold(
            backgroundColor: colors.cream50,
            body: body,
            bottomNavigationBar: AssenTabBar(
              items: items,
              currentIndex: currentIndex,
              onChanged: onChanged,
            ),
          );
        }

        // `atLeast` (not `== expanded`) so that un-collapsing large/XL from
        // expanded keeps this legacy path identical at 1200dp+: one boolean
        // drives BOTH the extended rail and the AssenContentColumn wrap below.
        final expanded = size.atLeast(AssenWindowSize.expanded);
        return Scaffold(
          backgroundColor: colors.cream50,
          body: Row(
            children: [
              DecoratedBox(
                decoration: BoxDecoration(
                  color: colors.cream100,
                  border: Border(right: BorderSide(color: colors.ink100)),
                ),
                child: NavigationRail(
                  backgroundColor: colors.cream100,
                  selectedIndex: currentIndex,
                  onDestinationSelected: onChanged,
                  extended: expanded,
                  labelType: expanded ? null : NavigationRailLabelType.selected,
                  useIndicator: true,
                  indicatorColor: colors.strawberryBg,
                  selectedIconTheme: IconThemeData(color: colors.roseMain),
                  unselectedIconTheme: IconThemeData(color: colors.ink500),
                  selectedLabelTextStyle: selectedRailLabelStyle,
                  unselectedLabelTextStyle: unselectedRailLabelStyle,
                  destinations: [
                    for (final item in items)
                      NavigationRailDestination(
                        icon: _RailIcon(item: item, active: false),
                        selectedIcon: _RailIcon(item: item, active: true),
                        label: Text(item.label),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: expanded
                    ? AssenContentColumn(maxWidth: contentMaxWidth, child: body)
                    : body,
              ),
            ],
          ),
        );
      },
    );
  }
}

/// A rail glyph with an optional count badge matching [AssenTabBar].
class _RailIcon extends StatelessWidget {
  const _RailIcon({required this.item, required this.active});

  final AssenTabItem item;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final glyph = Icon(active ? item.activeIcon : item.icon);
    if (item.badgeCount <= 0) return glyph;

    return Stack(
      clipBehavior: Clip.none,
      children: [
        glyph,
        Positioned(
          right: -SpacingTokens.s2,
          top: -SpacingTokens.s1,
          child: AssenCountBadge(count: item.badgeCount),
        ),
      ],
    );
  }
}
