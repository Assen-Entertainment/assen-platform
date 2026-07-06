import 'package:assen_mobile/src/app/router.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The login wall shown when a guest hits an auth-gated route (the 마이 tab).
///
/// Scaffold only: real social login is an E6 gate. For now it offers a
/// "게스트로 둘러보기" escape back to the public home so the guard never traps a
/// viewer. TODO(assen): add the social sign-in providers and, on success, set
/// the authenticated `AuthState` so the redirect releases the gate.
class LoginScreen extends StatelessWidget {
  /// Creates the login wall.
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const AssenAppBar(title: '로그인'),
      body: AssenEmptyState(
        title: '로그인이 필요해요',
        message: '소셜 로그인은 준비 중입니다. 먼저 게스트로 둘러볼 수 있어요.',
        actionLabel: '게스트로 둘러보기',
        onAction: () => context.go(RoutePaths.discovery),
      ),
    );
  }
}
