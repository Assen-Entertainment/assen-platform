import 'package:flutter/material.dart';
import 'package:ui_kit/ui_kit.dart';

/// The post-auth operator console shell chrome (대시보드/체크인/체키/신고/POS).
///
/// Mirrors fan_app's adaptive shell for the operator console: compact keeps a
/// bottom tab bar, Material 3 medium/expanded widths move the *same*
/// destinations into a navigation rail, and expanded constrains the body to
/// the wider console column ([AssenLayout.consoleContentMaxWidth]) — the
/// console is a working surface, so it gets more width than a reading column.
/// `/login` and `/admin` stay outside this shell, so the existing auth guard
/// and the deep-linkable admin slot are untouched.
///
/// This is a pure presentation widget: the router owns navigation by passing
/// the active [currentIndex] (derived from the location) and
/// [onDestinationSelected] (a `context.go` to the matching branch). Keeping it
/// router-agnostic lets the three-width behaviour be widget-tested without a
/// `GoRouter`.
class OperatorShell extends StatelessWidget {
  /// Creates the operator console shell around the active [child].
  const OperatorShell({
    required this.currentIndex,
    required this.onDestinationSelected,
    required this.child,
    super.key,
  });

  /// The selected destination index, shared by the rail and bottom bar.
  final int currentIndex;

  /// Called with the tapped destination index (router maps it to a location).
  final ValueChanged<int> onDestinationSelected;

  /// The active route's screen, rendered in the shell body.
  final Widget child;

  /// The console destinations, in navigation order.
  ///
  /// The index order is the single source of truth shared with the router's
  /// branch locations, so a tapped rail/tab destination resolves to the right
  /// route. `admin` is intentionally absent — it is a higher-role deep-link
  /// slot, not a primary console destination.
  static const List<AssenTabItem> destinations = [
    AssenTabItem(
      icon: Icons.dashboard_outlined,
      activeIcon: Icons.dashboard,
      label: '대시보드',
    ),
    AssenTabItem(
      icon: Icons.how_to_reg_outlined,
      activeIcon: Icons.how_to_reg,
      label: '체크인',
    ),
    AssenTabItem(
      icon: Icons.photo_camera_outlined,
      activeIcon: Icons.photo_camera,
      label: '체키',
    ),
    AssenTabItem(
      icon: Icons.calendar_month_outlined,
      activeIcon: Icons.calendar_month,
      label: '출근표',
    ),
    AssenTabItem(
      icon: Icons.report_outlined,
      activeIcon: Icons.report,
      label: '신고',
    ),
    AssenTabItem(
      icon: Icons.point_of_sale_outlined,
      activeIcon: Icons.point_of_sale,
      label: 'POS',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return AssenAdaptiveShell(
      currentIndex: currentIndex,
      onChanged: onDestinationSelected,
      items: destinations,
      contentMaxWidth: AssenLayout.consoleContentMaxWidth,
      body: child,
    );
  }
}
