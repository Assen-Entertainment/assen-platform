import 'package:flutter/material.dart';
import 'package:ui_kit/ui_kit.dart';

/// The operator dashboard (O1) — renders [AssenOperatorDashboardTemplate].
///
/// The template is a complete dashboard page (app bar + 신고 notice + segmented
/// views + stat grid + 예약 board), so it is reused whole. It is the operator's
/// post-auth root, so no back affordance is shown (onBack stays null). Mock
/// figures are operator-internal, not approved values (screens.md mock rule).
class OperatorDashboardScreen extends StatelessWidget {
  /// Creates the operator dashboard.
  const OperatorDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AssenOperatorDashboardTemplate();
  }
}
