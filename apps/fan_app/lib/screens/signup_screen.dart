import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The signup flow (A2 약관 → A3 본인인증 → A4 닉네임) as a static stub.
///
/// P3a renders the three steps with an [AssenStepIndicator] and advances them
/// locally (no backend); the final step signs in through the shared mock auth
/// and routes to /home, so the post-auth shell is reachable end to end. The
/// real verification/OTP wiring arrives later — here each step is a stub page
/// with the design-system frame.
class SignupScreen extends ConsumerStatefulWidget {
  /// Creates the signup flow.
  const SignupScreen({super.key});

  @override
  ConsumerState<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends ConsumerState<SignupScreen> {
  static const List<String> _steps = ['약관', '본인인증', '닉네임'];
  int _step = 0;

  bool get _isLast => _step == _steps.length - 1;

  Future<void> _advance() async {
    if (!_isLast) {
      setState(() => _step += 1);
      return;
    }
    await ref
        .read(authSessionProvider.notifier)
        .signIn(identifier: 'newfan@assen.example', password: 'mock');
    if (!mounted) return;
    context.go(FanRoutes.home);
  }

  void _back() {
    if (_step == 0) {
      context.go(FanRoutes.login);
      return;
    }
    setState(() => _step -= 1);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '가입', onBack: _back),
      bottomNavigationBar: AssenBottomCta(
        primaryLabel: _isLast ? '가입 완료' : '다음',
        onPrimary: _advance,
      ),
      body: SafeArea(
        child: AssenFormFrame(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AssenStepIndicator(
                  count: _steps.length,
                  currentStep: _step,
                  labels: _steps,
                ),
                const SizedBox(height: SpacingTokens.s8),
                Expanded(
                  child: Center(
                    child: _StepBody(label: _steps[_step], colors: colors),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// A simple per-step stub body (icon + the step's name).
class _StepBody extends StatelessWidget {
  const _StepBody({required this.label, required this.colors});

  final String label;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return AssenEmptyState(
      title: '$label 단계',
      message: '이 단계는 P3a 정적 스텁입니다.\n다음을 눌러 진행해요.',
      slot: Container(
        width: SpacingTokens.s16,
        height: SpacingTokens.s16,
        decoration: BoxDecoration(
          color: colors.strawberryBg,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(
          Icons.check_circle_outline,
          size: SpacingTokens.s8,
          color: colors.strawberryInk,
        ),
      ),
    );
  }
}
