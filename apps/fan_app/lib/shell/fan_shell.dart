import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The post-auth 5-tab shell chrome (홈/출근표/예약/체키/마이).
///
/// Owns the [AssenTabBar] for the whole shell so the per-tab screens render
/// only their own [AssenAppBar] + body. Tapping a tab drives
/// [StatefulNavigationShell.goBranch], which preserves each branch's state and
/// back stack (the IndexedStack); re-tapping the active tab pops it to its
/// root (the conventional tab-bar gesture). The shell body is the
/// [navigationShell] itself.
class FanShell extends StatelessWidget {
  /// Creates the shell around [navigationShell].
  const FanShell({required this.navigationShell, super.key});

  /// The shell navigator managing the five branch [Navigator]s.
  final StatefulNavigationShell navigationShell;

  void _onTap(int index) {
    // initialLocation: true when re-tapping the current tab resets it to the
    // branch root — the standard bottom-nav behaviour.
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      body: navigationShell,
      bottomNavigationBar: AssenTabBar(
        currentIndex: navigationShell.currentIndex,
        onChanged: _onTap,
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
      ),
    );
  }
}
