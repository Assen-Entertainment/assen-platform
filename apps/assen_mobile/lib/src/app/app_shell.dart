import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The persistent app scaffold hosting the four-tab bottom navigation.
///
/// go_router's [StatefulNavigationShell] renders the active branch (each tab
/// keeps its own navigation state via an IndexedStack) while this widget frames
/// it with the ui_kit [AssenTabBar]. The tab set matches the web IA:
/// 홈(discovery) · 검색(search) · 알림(notifications) · 마이(mypage).
class AppShell extends StatelessWidget {
  /// Creates the shell around the go_router-provided [navigationShell].
  const AppShell({required this.navigationShell, super.key});

  /// The shell that renders the current branch and switches tabs.
  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: AssenTabBar(
        currentIndex: navigationShell.currentIndex,
        onChanged: _goBranch,
        items: const [
          AssenTabItem(
            icon: Icons.home_outlined,
            activeIcon: Icons.home,
            label: '홈',
          ),
          AssenTabItem(icon: Icons.search, label: '검색'),
          AssenTabItem(
            icon: Icons.notifications_none,
            activeIcon: Icons.notifications,
            label: '알림',
          ),
          AssenTabItem(
            icon: Icons.person_outline,
            activeIcon: Icons.person,
            label: '마이',
          ),
        ],
      ),
    );
  }

  void _goBranch(int index) {
    // Re-tapping the active tab resets it to its initial route (common Korean
    // B2C behaviour), per go_router's recommended shell wiring.
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }
}
