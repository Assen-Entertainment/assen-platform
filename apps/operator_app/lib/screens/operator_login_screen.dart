import 'package:core_tokens/core_tokens.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/router/routes.dart';
import 'package:ui_kit/ui_kit.dart';

// Typography size literal until TypographyTokens lands (ASS-130).
const double _brandSize = 24; // display.s — operator wordmark

/// The operator login screen (static stub over the shared mock auth).
///
/// Signs in through the same [AuthSessionNotifier] the fan app uses (mock
/// today, real opaque-token client in P3b — CONSTRAINTS #31). The role判정 that
/// decides whether an operator may reach the console is a P3b concern; P3a only
/// authenticates, then the router forwards to /dashboard.
class OperatorLoginScreen extends ConsumerWidget {
  /// Creates the operator login screen.
  const OperatorLoginScreen({super.key});

  Future<void> _signIn(BuildContext context, WidgetRef ref) async {
    await ref
        .read(authSessionProvider.notifier)
        .signIn(identifier: 'operator@assen.example', password: 'mock');
    if (!context.mounted) return;
    context.go(OperatorRoutes.dashboard);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.screenMargin,
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '운영자 콘솔',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: _brandSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s8),
              const AssenTextField(label: '운영자 ID', hintText: '운영자 ID'),
              const SizedBox(height: SpacingTokens.s4),
              const AssenTextField(
                label: '비밀번호',
                hintText: '비밀번호',
                obscureText: true,
              ),
              const SizedBox(height: SpacingTokens.s8),
              AssenButton(
                label: '로그인',
                expand: true,
                onPressed: () => _signIn(context, ref),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
