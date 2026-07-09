import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/auth/dev_otp.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The steps of the phone-OTP sign-in flow.
enum _LoginStep {
  /// Enter the phone number and request an OTP.
  phone,

  /// Enter the received OTP to log in.
  otp,

  /// New number: capture a nickname + required consent to register.
  signup,
}

/// The login wall shown when a guest hits an auth-gated route (the 마이 tab).
///
/// Phone-OTP sign-in (mock OTP in dev/demo, ADR-0002 body-token surface): the
/// viewer requests a code, enters it to log in, and an unregistered number
/// falls through to a signup step (nickname + required 약관 동의). On success the
/// tokens are persisted in secure storage by [AuthController] and the viewer
/// lands on the 마이 tab. A "게스트로 둘러보기" escape keeps the guard from trapping a
/// viewer.
///
/// No real social login and no real payment (E6 subscription/purchase CTAs are
/// a later wave). The phone number is only sent to the OTP endpoints — it is
/// never stored on device.
class LoginScreen extends ConsumerStatefulWidget {
  /// Creates the login wall.
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _nicknameController = TextEditingController();

  _LoginStep _step = _LoginStep.phone;
  String _otp = '';
  AssenOtpStatus _otpStatus = AssenOtpStatus.entering;
  bool _consentTerms = false;
  bool _consentPrivacy = false;
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _phoneController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  String get _phone => _phoneController.text.trim();

  /// The deterministic mock OTP, shown as a hint in DEV builds only so a demo
  /// tester can complete the mock login. Never derived in a release build.
  String? get _devOtpHint => kReleaseMode ? null : devMockOtpCode(_phone);

  /// Requests an OTP for the entered phone and advances to the code step.
  Future<void> _sendOtp() async {
    if (_phone.isEmpty) {
      setState(() => _errorText = '휴대폰 번호를 입력해 주세요.');
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref.read(authControllerProvider.notifier).requestOtp(_phone);
      if (!mounted) return;
      setState(() {
        _step = _LoginStep.otp;
        _otp = '';
        _otpStatus = AssenOtpStatus.entering;
      });
    } on AuthException catch (error) {
      _fail(error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Logs in with the entered OTP; an unregistered number falls to signup.
  Future<void> _login() async {
    setState(() {
      _busy = true;
      _errorText = null;
      _otpStatus = AssenOtpStatus.entering;
    });
    try {
      await ref
          .read(authControllerProvider.notifier)
          .login(phone: _phone, otp: _otp);
      _goHome();
    } on AuthException catch (error) {
      if (!mounted) return;
      switch (error.reason) {
        case AuthFailureReason.accountNotRegistered:
          setState(() {
            _step = _LoginStep.signup;
            _errorText = null;
          });
        case AuthFailureReason.invalidOtp:
          setState(() {
            _otpStatus = AssenOtpStatus.error;
            _errorText = error.message;
          });
        case AuthFailureReason.invalidPhone:
        case AuthFailureReason.consentRequired:
        case AuthFailureReason.unavailable:
        case AuthFailureReason.unknown:
          setState(() => _errorText = error.message);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Registers a new fan with the captured nickname + consent.
  Future<void> _signup() async {
    final nickname = _nicknameController.text.trim();
    if (nickname.isEmpty || nickname.runes.length > 40) {
      setState(() => _errorText = '닉네임은 1~40자로 입력해 주세요.');
      return;
    }
    if (!_consentTerms || !_consentPrivacy) {
      setState(() => _errorText = '필수 약관에 모두 동의해 주세요.');
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref
          .read(authControllerProvider.notifier)
          .signup(
            phone: _phone,
            otp: _otp,
            nickname: nickname,
            consentTerms: _consentTerms,
            consentPrivacy: _consentPrivacy,
          );
      _goHome();
    } on AuthException catch (error) {
      _fail(error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _fail(String message) {
    if (!mounted) return;
    setState(() => _errorText = message);
  }

  void _goHome() {
    if (!mounted) return;
    context.go(RoutePaths.mypage);
  }

  /// Steps back one screen (or leaves the wall from the first step).
  void _back() {
    switch (_step) {
      case _LoginStep.phone:
        context.go(RoutePaths.discovery);
      case _LoginStep.otp:
        setState(() {
          _step = _LoginStep.phone;
          _errorText = null;
        });
      case _LoginStep.signup:
        setState(() {
          _step = _LoginStep.otp;
          _errorText = null;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AssenAppBar(
        title: _step == _LoginStep.signup ? '회원가입' : '로그인',
        onBack: _back,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(SpacingTokens.s4),
          child: switch (_step) {
            _LoginStep.phone => _PhoneStep(
              controller: _phoneController,
              busy: _busy,
              errorText: _errorText,
              onSubmit: _sendOtp,
              onGuest: () => context.go(RoutePaths.discovery),
            ),
            _LoginStep.otp => _OtpStep(
              phone: _phone,
              status: _otpStatus,
              errorText: _errorText,
              devOtpHint: _devOtpHint,
              busy: _busy,
              onChanged: (value) => _otp = value,
              onSubmit: _login,
              onResend: _sendOtp,
            ),
            _LoginStep.signup => _SignupStep(
              controller: _nicknameController,
              consentTerms: _consentTerms,
              consentPrivacy: _consentPrivacy,
              busy: _busy,
              errorText: _errorText,
              onTermsChanged: (v) => setState(() => _consentTerms = v),
              onPrivacyChanged: (v) => setState(() => _consentPrivacy = v),
              onSubmit: _signup,
            ),
          },
        ),
      ),
    );
  }
}

/// Step 1 — the phone-number entry and OTP request.
class _PhoneStep extends StatelessWidget {
  const _PhoneStep({
    required this.controller,
    required this.busy,
    required this.errorText,
    required this.onSubmit,
    required this.onGuest,
  });

  final TextEditingController controller;
  final bool busy;
  final String? errorText;
  final VoidCallback onSubmit;
  final VoidCallback onGuest;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const AssenReveal(child: _BrandFrontDoor()),
        const SizedBox(height: SpacingTokens.s6),
        AssenReveal(
          index: 1,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '휴대폰 번호로 시작하기',
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                '인증번호를 보내드릴게요. 소셜 로그인은 준비 중이에요.',
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  color: colors.ink600,
                ),
              ),
              const SizedBox(height: SpacingTokens.s6),
              AssenTextField(
                label: '휴대폰 번호',
                controller: controller,
                hintText: '010-1234-5678',
                keyboardType: TextInputType.phone,
                errorText: errorText,
                prefixIcon: Icons.phone_outlined,
              ),
              const SizedBox(height: SpacingTokens.s6),
              AssenButton(
                label: '인증번호 받기',
                expand: true,
                onPressed: busy ? null : onSubmit,
              ),
              const SizedBox(height: SpacingTokens.s2),
              AssenButton(
                label: '게스트로 둘러보기',
                style: AssenButtonStyle.ghost,
                expand: true,
                onPressed: busy ? null : onGuest,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// The login brand front-door — the mobile analogue of the web `AuthShell`.
///
/// A gradient brand panel carrying the white [AssenLogo] lockup and a short
/// tagline, shown on the first sign-in step. The gradient is the sanctioned
/// tokens.md 2026-07-09 exception (login surface); it adds no logic to the
/// OTP/mock flow. White copy reads AA on [AssenGradients.brand] at every stop.
class _BrandFrontDoor extends StatelessWidget {
  const _BrandFrontDoor();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        vertical: SpacingTokens.s8,
        horizontal: SpacingTokens.s5,
      ),
      decoration: const BoxDecoration(
        gradient: AssenGradients.brand,
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.xl)),
        boxShadow: [
          BoxShadow(
            color: ElevationTokens.level1Color,
            offset: Offset(
              ElevationTokens.level1OffsetX,
              ElevationTokens.level1OffsetY,
            ),
            blurRadius: ElevationTokens.level1Blur,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const AssenLogo(
            size: AssenLogoSize.lg,
            mono: true,
            color: AssenGradients.onBrand,
          ),
          const SizedBox(height: SpacingTokens.s4),
          Text(
            '크리에이터를 응원하는 가장 가까운 방법',
            textAlign: TextAlign.center,
            style: TypographyTokens.bodyM.copyWith(
              color: AssenGradients.onBrand,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

/// Step 2 — enter the received OTP and log in.
class _OtpStep extends StatelessWidget {
  const _OtpStep({
    required this.phone,
    required this.status,
    required this.errorText,
    required this.devOtpHint,
    required this.busy,
    required this.onChanged,
    required this.onSubmit,
    required this.onResend,
  });

  final String phone;
  final AssenOtpStatus status;
  final String? errorText;
  final String? devOtpHint;
  final bool busy;
  final ValueChanged<String> onChanged;
  final VoidCallback onSubmit;
  final VoidCallback onResend;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '인증번호 입력',
          style: TextStyle(
            fontSize: TypographyTokens.headlineSize,
            fontWeight: FontWeight.w800,
            color: colors.ink900,
          ),
        ),
        const SizedBox(height: SpacingTokens.s2),
        Text(
          '$phone(으)로 보낸 6자리 인증번호를 입력해 주세요.',
          style: TextStyle(
            fontSize: TypographyTokens.bodyMSize,
            color: colors.ink600,
          ),
        ),
        if (devOtpHint != null) ...[
          const SizedBox(height: SpacingTokens.s3),
          // DEV/MOCK ONLY: derived locally to demo the mock login; never shown
          // in a release build (guarded by kReleaseMode in the screen).
          AssenNoticeBar(message: '개발용 인증번호: $devOtpHint'),
        ],
        const SizedBox(height: SpacingTokens.s6),
        AssenOtpField(
          onChanged: onChanged,
          status: status,
          errorText: errorText,
        ),
        const SizedBox(height: SpacingTokens.s6),
        AssenButton(
          label: '로그인',
          expand: true,
          onPressed: busy ? null : onSubmit,
        ),
        const SizedBox(height: SpacingTokens.s2),
        AssenButton(
          label: '인증번호 다시 받기',
          style: AssenButtonStyle.ghost,
          expand: true,
          onPressed: busy ? null : onResend,
        ),
      ],
    );
  }
}

/// Step 3 — a new number: capture nickname + required consent to register.
class _SignupStep extends StatelessWidget {
  const _SignupStep({
    required this.controller,
    required this.consentTerms,
    required this.consentPrivacy,
    required this.busy,
    required this.errorText,
    required this.onTermsChanged,
    required this.onPrivacyChanged,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool consentTerms;
  final bool consentPrivacy;
  final bool busy;
  final String? errorText;
  final ValueChanged<bool> onTermsChanged;
  final ValueChanged<bool> onPrivacyChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '처음 오셨네요! 가입을 마저 진행할게요',
          style: TextStyle(
            fontSize: TypographyTokens.headlineSize,
            fontWeight: FontWeight.w800,
            color: colors.ink900,
          ),
        ),
        const SizedBox(height: SpacingTokens.s6),
        AssenTextField(
          label: '닉네임',
          controller: controller,
          hintText: '사용할 닉네임',
          helperText: '1~40자',
        ),
        const SizedBox(height: SpacingTokens.s6),
        const AssenSectionHeader(title: '약관 동의'),
        AssenAgreementCell(
          label: '서비스 이용약관 동의',
          value: consentTerms,
          onChanged: onTermsChanged,
        ),
        AssenAgreementCell(
          label: '개인정보 수집·이용 동의',
          value: consentPrivacy,
          onChanged: onPrivacyChanged,
        ),
        if (errorText != null) ...[
          const SizedBox(height: SpacingTokens.s3),
          Text(
            errorText!,
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              color: colors.redMain,
            ),
          ),
        ],
        const SizedBox(height: SpacingTokens.s6),
        AssenButton(
          label: '가입하고 시작하기',
          expand: true,
          onPressed: busy ? null : onSubmit,
        ),
      ],
    );
  }
}
