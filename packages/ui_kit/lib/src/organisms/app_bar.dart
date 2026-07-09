import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';

/// The top app bar (`기본형 — 센터 타이틀`).
///
/// Covers the Navigation/AppBar row of `components.md`. A centre-titled bar that
/// sits on the cream container surface with an optional back affordance and a
/// trailing action slot. It wraps Material's [AppBar] so the colours, the 44pt
/// touch targets and the centred title come from the Assen tokens rather than
/// each screen re-theming the frame. Implements [PreferredSizeWidget] so it
/// drops straight into a [Scaffold.appBar].
class AssenAppBar extends StatelessWidget implements PreferredSizeWidget {
  /// Creates a centre-titled app bar showing [title].
  ///
  /// Set [onBack] to show a leading back button (omit it on a tab root).
  /// [actions] are trailing affordances (e.g. an [AssenIconButton]); keep to a
  /// couple so the centred [title] stays balanced. [showDivider] paints a
  /// hairline bottom border for screens that scroll under the bar.
  const AssenAppBar({
    required this.title,
    this.onBack,
    this.actions = const [],
    this.showDivider = false,
    super.key,
  });

  /// The centred screen title.
  final String title;

  /// Optional back handler; when set, a leading back button is shown.
  final VoidCallback? onBack;

  /// Trailing action widgets rendered after the title.
  final List<Widget> actions;

  /// Whether to paint a hairline divider under the bar.
  final bool showDivider;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AppBar(
      backgroundColor: colors.neutral100,
      foregroundColor: colors.ink900,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: true,
      titleSpacing: 0,
      leading: onBack == null
          ? null
          : AssenIconButton(
              icon: Icons.arrow_back_ios_new,
              semanticLabel: '뒤로',
              onPressed: onBack,
            ),
      title: Semantics(
        header: true,
        child: Text(
          title,
          style: TextStyle(
            fontSize: TypographyTokens.titleLSize,
            fontWeight: FontWeight.w700,
            color: colors.ink900,
          ),
        ),
      ),
      actions: actions,
      bottom: showDivider
          ? PreferredSize(
              preferredSize: const Size.fromHeight(1),
              child: Container(height: 1, color: colors.neutral100),
            )
          : null,
    );
  }
}

/// A single destination in the [AssenTabBar] (label + icons + optional badge).
///
/// The [icon]/[activeIcon] pair lets the active tab swap to a filled glyph
/// (a common Korean B2C convention for the home indicator). [badgeCount]
/// overlays an [AssenCountBadge] for unread markers (e.g. notifications).
class AssenTabItem {
  /// Creates a tab destination.
  const AssenTabItem({
    required this.icon,
    required this.label,
    IconData? activeIcon,
    this.badgeCount = 0,
  }) : activeIcon = activeIcon ?? icon;

  /// The resting (unselected) glyph.
  final IconData icon;

  /// The selected glyph (defaults to [icon] when omitted).
  final IconData activeIcon;

  /// The tab label.
  final String label;

  /// Unread count overlaid as a badge; 0 hides it.
  final int badgeCount;
}

/// The bottom navigation bar (`TabBar(Bottom) — active 표시`).
///
/// Covers the Navigation/TabBar row of `components.md`. A domain-neutral bottom
/// nav: the host app supplies its own destinations. The active tab is shown
/// with the rose action colour and a filled glyph; inactive tabs use the
/// secondary ink. It wraps Material [BottomNavigationBar] so every tab keeps a
/// 44pt+ target and reads its colours from the tokens. Unread badges ride on
/// top via [AssenCountBadge].
class AssenTabBar extends StatelessWidget {
  /// Creates the bottom tab bar.
  ///
  /// [items] are the destinations supplied by the host app. [currentIndex] is
  /// the selected tab; [onChanged] reports taps. Asserts two+ destinations.
  const AssenTabBar({
    required this.items,
    required this.currentIndex,
    required this.onChanged,
    super.key,
  }) : assert(items.length >= 2, 'A tab bar needs at least two destinations');

  /// The tab destinations supplied by the host app.
  final List<AssenTabItem> items;

  /// The currently selected tab index.
  final int currentIndex;

  /// Called with the tapped tab index.
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.white,
        border: Border(top: BorderSide(color: colors.neutral100)),
      ),
      child: BottomNavigationBar(
        currentIndex: currentIndex,
        onTap: onChanged,
        type: BottomNavigationBarType.fixed,
        backgroundColor: Colors.transparent,
        elevation: 0,
        selectedItemColor: colors.indigo500,
        unselectedItemColor: colors.ink500,
        selectedFontSize: TypographyTokens.captionMicroSize,
        unselectedFontSize: TypographyTokens.captionMicroSize,
        items: [
          for (var i = 0; i < items.length; i++)
            BottomNavigationBarItem(
              icon: _TabIcon(item: items[i], active: false, colors: colors),
              activeIcon: _TabIcon(
                item: items[i],
                active: true,
                colors: colors,
              ),
              label: items[i].label,
            ),
        ],
      ),
    );
  }
}

/// A tab glyph with an optional count badge overlay.
class _TabIcon extends StatelessWidget {
  const _TabIcon({
    required this.item,
    required this.active,
    required this.colors,
  });

  final AssenTabItem item;
  final bool active;
  final AssenColors colors;

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
