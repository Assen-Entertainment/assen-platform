import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/mock/fan_mock_data.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The rotating QR check-in screen (B1) — a deep-link entry point (`/qr`).
///
/// Presents the [AssenQrDisplay] for staff to scan. P3a is static: the code is
/// the organism's placeholder matrix and the rotation does not tick; a dev-only
/// "체크인 완료" action stands in for a successful scan, routing to /checkin/
/// complete. Reaching `/qr` while unauthenticated is sent to /login with a
/// return_to=/qr by the guard, then back here after sign-in (acceptance: QR
/// entry redirect-and-resume).
class QrScreen extends StatelessWidget {
  /// Creates the QR check-in screen.
  const QrScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: '체크인 QR',
        onBack: () => _pop(context),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(SpacingTokens.screenMargin),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AssenQrDisplay(
                memberNumber: FanMockData.member.memberNumber,
                remainingLabel: '29초',
              ),
              const SizedBox(height: SpacingTokens.s8),
              AssenButton(
                label: '체크인 완료 (데모)',
                expand: true,
                onPressed: () => context.go(FanRoutes.checkinComplete),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _pop(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(FanRoutes.home);
    }
  }
}
