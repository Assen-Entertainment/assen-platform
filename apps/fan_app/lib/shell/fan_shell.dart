import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Compile-time guard for the desktop sidebar shell (ASS-147 Slice 1).
///
/// `true` routes the fan shell through [AssenSidebarShell] (persistent sidebar
/// at large/XL, full-width body). Flip to `false` for a one-line rollback to the
/// previous [AssenAdaptiveShell] (rail + 1280 reading column) without touching
/// any screen. Below the large window size class both paths are identical.
const bool kAssenWebDesktopV2 = true;

/// The post-auth 5-destination shell chrome (홈/출근표/예약/체키/마이).
///
/// Owns the adaptive shell so per-tab screens render only their own
/// [AssenAppBar] + body. Compact widths keep the existing bottom tab bar;
/// medium/expanded use a navigation rail; large/XL desktop widths use a
/// persistent [AssenSidebarShell] sidebar with a full-width body. Tapping a
/// destination drives [StatefulNavigationShell.goBranch], preserving each
/// branch's IndexedStack state; re-tapping the active destination pops it to
/// its root.
class FanShell extends StatelessWidget {
  /// Creates the shell around [navigationShell].
  const FanShell({required this.navigationShell, super.key});

  /// The shell navigator managing the five branch [Navigator]s.
  final StatefulNavigationShell navigationShell;

  void _onTap(int index) {
    // initialLocation: true when re-tapping the current tab resets it to the
    // branch root, which is the standard mobile bottom-nav behaviour.
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  static const List<AssenTabItem> _destinations = [
    AssenTabItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: '홈'),
    AssenTabItem(
      icon: Icons.calendar_month_outlined,
      activeIcon: Icons.calendar_month,
      label: '출근표',
    ),
    AssenTabItem(icon: Icons.event_outlined, label: '예약'),
    AssenTabItem(
      icon: Icons.photo_library_outlined,
      label: '체키',
      badgeCount: 3,
    ),
    AssenTabItem(icon: Icons.person_outline, label: '마이'),
  ];

  @override
  Widget build(BuildContext context) {
    if (!kAssenWebDesktopV2) {
      return AssenAdaptiveShell(
        currentIndex: navigationShell.currentIndex,
        onChanged: _onTap,
        body: navigationShell,
        items: _destinations,
      );
    }
    return AssenSidebarShell(
      currentIndex: navigationShell.currentIndex,
      onChanged: _onTap,
      body: navigationShell,
      items: _destinations,
      header: const _FanSidebarBrand(),
    );
  }
}

/// The brand wordmark pinned at the top of the desktop sidebar.
class _FanSidebarBrand extends StatelessWidget {
  const _FanSidebarBrand();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Row(
      children: [
        Icon(Icons.local_cafe, color: colors.roseMain, size: SpacingTokens.s6),
        const SizedBox(width: SpacingTokens.s2),
        Text(
          '하츠코이',
          style: TypographyTokens.titleM.copyWith(color: colors.strawberryInk),
        ),
      ],
    );
  }
}
