import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The post-auth 5-destination shell chrome (홈/출근표/예약/체키/마이).
///
/// Owns [AssenAdaptiveShell] for the whole shell so per-tab screens render only
/// their own [AssenAppBar] + body. Compact widths keep the existing bottom tab
/// bar; Material 3 medium/expanded widths move the same destinations into a
/// navigation rail and constrain expanded content for web/tablet readability.
/// Tapping a destination drives [StatefulNavigationShell.goBranch], preserving
/// each branch's IndexedStack state; re-tapping the active destination pops it
/// to its root.
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

  @override
  Widget build(BuildContext context) {
    return AssenAdaptiveShell(
      currentIndex: navigationShell.currentIndex,
      onChanged: _onTap,
      body: navigationShell,
      items: const [
        AssenTabItem(
          icon: Icons.home_outlined,
          activeIcon: Icons.home,
          label: '홈',
        ),
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
      ],
    );
  }
}
