import 'package:assen_mobile/src/settings/settings_controller.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:assen_mobile/src/verify/verify_gate.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 본인인증(KYC) screen the global gate routes an unverified fan to.
///
/// Reached when the server refuses a gated interaction (follow/구독/구매/댓글/
/// 좋아요) with a 403 `IdentityVerificationRequired`: the `KycGateInterceptor`
/// raises [kycGateProvider] and the router redirects here, carrying the origin
/// location as `?next=` so the fan returns to what they were doing. Reading is
/// never gated, and the verify endpoints themselves are not gated, so this
/// screen is always reachable.
///
/// Runs the same `verify/start` → `verify/confirm` flow the 설정 screen's 19+
/// action uses (reusing [SettingsRepository.verifyAdult]) and then refreshes
/// the session profile so `kyc_status` updates. The mock verifier passes
/// immediately (real PASS/NICE/KCB integration is a 대표·법무 gate); only the
/// derived `adult_verified`/`kyc_status` flags cross the wire — never
/// 주민번호/생년월일.
class VerifyScreen extends ConsumerStatefulWidget {
  /// Creates the 본인인증 screen returning to [next] when done.
  const VerifyScreen({required this.next, super.key});

  /// The location to return to once verification completes (or is abandoned).
  final String next;

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  bool _consentIdentity = false;
  bool _consentTerms = false;
  bool _consentPrivacy = false;
  bool _busy = false;
  String? _noticeText;
  String? _errorText;

  bool get _consented => _consentIdentity && _consentTerms && _consentPrivacy;

  /// Runs 본인인증, then releases the gate and returns to the origin.
  Future<void> _verify() async {
    if (!_consented) {
      setState(() => _errorText = '필수 항목에 모두 동의해 주세요.');
      return;
    }
    setState(() {
      _busy = true;
      _noticeText = null;
      _errorText = null;
    });
    try {
      await ref.read(settingsRepositoryProvider).verifyAdult();
      // Re-read the profile so the 인증 flags the 설정/마이 badges show reflect the
      // new state rather than the stale pre-verify snapshot.
      ref.invalidate(settingsControllerProvider);
      _leave();
    } on KycUnavailableException {
      if (!mounted) return;
      setState(() => _noticeText = '본인인증 준비 중이에요. 잠시 후 다시 시도해 주세요.');
    } on SettingsAuthRequiredException {
      // The session expired mid-verify: release the gate and let the router's
      // auth guard take the fan to the login wall.
      _leave();
    } on Exception {
      if (!mounted) return;
      setState(() => _errorText = '인증하지 못했어요. 잠시 후 다시 시도해 주세요.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Releases the gate and returns to the origin location.
  ///
  /// Clearing the flag first is what lets the router's redirect fall through —
  /// while it is raised every location resolves back to this screen.
  void _leave() {
    ref.read(kycGateProvider.notifier).clear();
    if (!mounted) return;
    context.go(widget.next);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Scaffold(
      appBar: AssenAppBar(title: '본인인증', onBack: _leave),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(SpacingTokens.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '본인인증',
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                '팔로우·구독·구매 등 서비스 이용을 위해 본인인증이 필요해요. 아래 항목에 동의 후 진행해 주세요.',
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  color: colors.ink600,
                ),
              ),
              if (_noticeText != null) ...[
                const SizedBox(height: SpacingTokens.s4),
                AssenNoticeBar(message: _noticeText!),
              ],
              const SizedBox(height: SpacingTokens.s6),
              const AssenSectionHeader(title: '약관 동의'),
              AssenAgreementCell(
                label: '본인확인 동의',
                value: _consentIdentity,
                onChanged: (v) => setState(() => _consentIdentity = v),
              ),
              AssenAgreementCell(
                label: '이용약관 동의',
                value: _consentTerms,
                onChanged: (v) => setState(() => _consentTerms = v),
              ),
              AssenAgreementCell(
                label: '개인정보 처리방침 동의',
                value: _consentPrivacy,
                onChanged: (v) => setState(() => _consentPrivacy = v),
              ),
              if (_errorText != null) ...[
                const SizedBox(height: SpacingTokens.s3),
                Text(
                  _errorText!,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.redMain,
                  ),
                ),
              ],
              const SizedBox(height: SpacingTokens.s6),
              AssenButton(
                label: '본인인증하기',
                expand: true,
                onPressed: _busy || !_consented ? null : _verify,
              ),
              const SizedBox(height: SpacingTokens.s3),
              Text(
                '※ 본인인증은 파생 플래그만 저장하며 주민번호·생년월일 원본은 보관하지 않아요.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink600,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              AssenButton(
                label: '다음에 하기',
                style: AssenButtonStyle.ghost,
                expand: true,
                onPressed: _busy ? null : _leave,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
