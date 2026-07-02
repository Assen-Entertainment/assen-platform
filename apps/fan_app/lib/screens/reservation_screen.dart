import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The reservation tab (D1) — an [AssenEmptyState] placeholder (no template
/// yet).
///
/// D1 has no ui_kit template, so P3a ships the empty-reservation surface using
/// the design-system [AssenEmptyState] (never a grey box — screens.md 밀도
/// 규칙), with a CTA to browse the schedule. The real date/time/party picker
/// lands later.
class ReservationScreen extends StatelessWidget {
  /// Creates the reservation tab placeholder.
  const ReservationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '예약'),
      body: AssenEmptyState(
        title: '아직 예약이 없어요',
        message: '출근표에서 최애의 일정을 확인하고\n방문을 예약해 보세요.',
        slot: Container(
          width: SpacingTokens.s16,
          height: SpacingTokens.s16,
          decoration: BoxDecoration(
            color: colors.skyBg,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Icon(
            Icons.event_available_outlined,
            size: SpacingTokens.s8,
            color: colors.skyInk,
          ),
        ),
        actionLabel: '출근표 보기',
        onAction: () => context.go(FanRoutes.schedule),
      ),
    );
  }
}
