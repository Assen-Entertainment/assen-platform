import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

// Typography size literal until TypographyTokens lands (ASS-130).
const double _brandSize = 28; // display.m — wordmark

/// The login screen (Flutter web entry point; static stub over the mock auth).
///
/// Signs in through the shared [AuthSessionNotifier] (mock today, real
/// opaque-token client in P3b — CONSTRAINTS #31). On success the router's guard
/// forwards the user to their original destination ([returnTo]) or /home. The
/// form is a minimal stub (a single primary CTA, Korean B2C convention #1); the
/// real A2/A3/A4 flow is reached via 가입.
class LoginScreen extends ConsumerWidget {
  /// Creates the login screen. [returnTo] is the safe in-app path to resume
  /// after authentication (already validated by the router from the landing
  /// handoff or a deep-link redirect).
  const LoginScreen({this.returnTo, super.key});

  /// The post-login destination, or null to use the default (/home).
  final String? returnTo;

  Future<void> _signIn(BuildContext context, WidgetRef ref) async {
    // The stub accepts any non-empty credentials; the real client validates.
    await ref
        .read(authSessionProvider.notifier)
        .signIn(identifier: 'fan@assen.example', password: 'mock');
    if (!context.mounted) return;
    context.go(returnTo ?? FanRoutes.home);
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
                '하츠코이',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: _brandSize,
                  fontWeight: FontWeight.w800,
                  color: colors.strawberryInk,
                ),
              ),
              const SizedBox(height: SpacingTokens.s8),
              // P3a stub: the fields are decorative (no controllers) — input
              // is ignored and sign-in uses fixed mock credentials.
              const AssenTextField(
                label: '아이디',
                hintText: '아이디 또는 이메일',
              ),
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
              const SizedBox(height: SpacingTokens.s2),
              AssenButton(
                label: '가입하기',
                style: AssenButtonStyle.ghost,
                expand: true,
                onPressed: () => context.go(FanRoutes.signup),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
