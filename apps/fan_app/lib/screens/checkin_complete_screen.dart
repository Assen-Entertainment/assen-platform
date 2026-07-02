import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The check-in complete screen (B2) — a completion placeholder.
///
/// Shown after the rotating QR (B1) is accepted. P3a renders a success state
/// with a CTA back to home; the real point-accrual feedback arrives later.
class CheckinCompleteScreen extends StatelessWidget {
  /// Creates the check-in complete placeholder.
  const CheckinCompleteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: '체크인 완료',
        onBack: () => context.go(FanRoutes.home),
      ),
      body: AssenEmptyState(
        title: '체크인이 완료되었어요',
        message: '방문이 기록되었습니다.\n스탬프와 적립은 곧 반영돼요.',
        slot: Container(
          width: SpacingTokens.s16,
          height: SpacingTokens.s16,
          decoration: BoxDecoration(
            color: colors.matchaBg,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Icon(
            Icons.check_rounded,
            size: SpacingTokens.s10,
            color: colors.matchaInk,
          ),
        ),
        actionLabel: '홈으로',
        onAction: () => context.go(FanRoutes.home),
      ),
    );
  }
}
