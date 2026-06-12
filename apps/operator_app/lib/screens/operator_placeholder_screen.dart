import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/router/routes.dart';
import 'package:ui_kit/ui_kit.dart';

/// A generic operator placeholder page (O2–O5, admin) — no template yet.
///
/// The check-in/cheki/reports/POS/admin surfaces have no ui_kit template in
/// P3a, so each is a design-system [AssenEmptyState] (never a grey box —
/// screens.md 밀도 규칙) under a titled bar, with a back affordance to the
/// dashboard. The real tools land later.
class OperatorPlaceholderScreen extends StatelessWidget {
  /// Creates a placeholder titled [title] with a one-line [message].
  const OperatorPlaceholderScreen({
    required this.title,
    required this.message,
    required this.icon,
    super.key,
  });

  /// The app-bar title (the surface name, e.g. "체크인 처리").
  final String title;

  /// The supporting line under the empty-state headline.
  final String message;

  /// The motif glyph shown in the pastel slot.
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: title,
        onBack: () => _pop(context),
      ),
      body: AssenEmptyState(
        title: title,
        message: message,
        slot: Container(
          width: SpacingTokens.s16,
          height: SpacingTokens.s16,
          decoration: BoxDecoration(
            color: colors.skyBg,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Icon(icon, size: SpacingTokens.s8, color: colors.skyInk),
        ),
      ),
    );
  }

  void _pop(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(OperatorRoutes.dashboard);
    }
  }
}
