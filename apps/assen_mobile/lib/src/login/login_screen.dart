import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The steps of the email sign-in flow.
enum _LoginStep {
  /// Enter an email + password to sign in.
  login,

  /// Register: email + password + nickname + required consent.
  signup,

  /// Signup accepted — tell the fan to open the verification mail.
  verificationSent,
}

/// The minimum password length the server enforces (`EmailSignupIn`, min 8).
const int _minPasswordLength = 8;

/// The login wall shown when a guest hits an auth-gated route (the 마이 tab).
///
/// Email + password sign-in (ADR-0002 body-token surface): the viewer signs in,
/// or registers and confirms the emailed verification link — the server issues
/// no session until that link is confirmed. On success the tokens are persisted
/// in secure storage by [AuthController] and the viewer lands on the 마이 tab. A
/// "게스트로 둘러보기" escape keeps the guard from trapping a viewer.
///
/// Social login (kakao/google/naver) needs OAuth deep links + provider
/// redirect-URI registration and is a later wave. The email/password are only
/// sent to the auth endpoints — never stored on device, logged, or held in an
/// exception.
class LoginScreen extends ConsumerStatefulWidget {
  /// Creates the login wall.
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nicknameController = TextEditingController();

  _LoginStep _step = _LoginStep.login;
  bool _consentTerms = false;
  bool _consentPrivacy = false;
  bool _ageOver14 = false;
  bool _marketingConsent = false;
  bool _busy = false;
  String? _errorText;

  /// The verification token echoed by a dev/test server
  /// (`EMAIL_VERIFY_RETURN_TOKEN`), enabling the "인증 완료(개발용)" affordance.
  /// Empty on any real surface, where the fan must open the mailed link.
  String _verificationToken = '';

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  String get _email => _emailController.text.trim();
  String get _password => _passwordController.text;

  /// Signs in with the entered email + password.
  Future<void> _login() async {
    if (_email.isEmpty || _password.isEmpty) {
      setState(() => _errorText = '이메일과 비밀번호를 입력해 주세요.');
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref
          .read(authControllerProvider.notifier)
          .loginEmail(email: _email, password: _password);
      _goHome();
    } on AuthException catch (error) {
      _fail(error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Registers a new fan; on success the flow waits on the verification mail.
  Future<void> _signup() async {
    final nickname = _nicknameController.text.trim();
    if (_email.isEmpty) {
      setState(() => _errorText = '이메일을 입력해 주세요.');
      return;
    }
    if (_password.length < _minPasswordLength) {
      setState(() => _errorText = '비밀번호는 8자 이상으로 입력해 주세요.');
      return;
    }
    if (nickname.isEmpty || nickname.runes.length > 40) {
      setState(() => _errorText = '닉네임은 1~40자로 입력해 주세요.');
      return;
    }
    if (!_consentTerms || !_consentPrivacy || !_ageOver14) {
      setState(() => _errorText = '필수 약관에 모두 동의해 주세요.');
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      final token = await ref
          .read(authControllerProvider.notifier)
          .signupEmail(
            email: _email,
            password: _password,
            nickname: nickname,
            consentTerms: _consentTerms,
            consentPrivacy: _consentPrivacy,
            ageOver14: _ageOver14,
            marketingConsent: _marketingConsent,
          );
      if (!mounted) return;
      setState(() {
        _verificationToken = token;
        _step = _LoginStep.verificationSent;
        _errorText = null;
      });
    } on AuthException catch (error) {
      if (!mounted) return;
      switch (error.reason) {
        case AuthFailureReason.emailAlreadyRegistered:
          // The address is already registered: drop back to the sign-in step
          // with the address kept, so the fan can just enter their password.
          setState(() {
            _step = _LoginStep.login;
            _errorText = error.message;
          });
        case AuthFailureReason.invalidCredentials:
          // On signup this code only ever means the password floor (the length
          // is pre-checked above, so this is the server's belt-and-braces).
          setState(() => _errorText = '비밀번호는 8자 이상으로 입력해 주세요.');
        case AuthFailureReason.emailNotVerified:
        case AuthFailureReason.emailVerificationInvalid:
        case AuthFailureReason.consentRequired:
        case AuthFailureReason.underage:
        case AuthFailureReason.unavailable:
        case AuthFailureReason.unknown:
          setState(() => _errorText = error.message);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// DEV/QA ONLY — completes verification with the server-echoed token.
  ///
  /// A dev/test server returns the token from signup so the flow can be closed
  /// without an inbox (mirroring the web's "인증 링크 열기(개발용)"). The button is
  /// only rendered when the token is non-empty, which never happens on a real
  /// surface — there the fan opens the mailed link instead.
  Future<void> _confirmVerification() async {
    setState(() {
      _busy = true;
      _errorText = null;
    });
    try {
      await ref
          .read(authControllerProvider.notifier)
          .verifyEmail(_verificationToken);
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
      case _LoginStep.login:
        context.go(RoutePaths.discovery);
      case _LoginStep.signup:
      case _LoginStep.verificationSent:
        setState(() {
          _step = _LoginStep.login;
          _errorText = null;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AssenAppBar(
        title: _step == _LoginStep.login ? '로그인' : '회원가입',
        onBack: _back,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(SpacingTokens.s4),
          child: switch (_step) {
            _LoginStep.login => _LoginStepView(
              emailController: _emailController,
              passwordController: _passwordController,
              busy: _busy,
              errorText: _errorText,
              onSubmit: _login,
              onSignup: () => setState(() {
                _step = _LoginStep.signup;
                _errorText = null;
              }),
              onGuest: () => context.go(RoutePaths.discovery),
            ),
            _LoginStep.signup => _SignupStepView(
              emailController: _emailController,
              passwordController: _passwordController,
              nicknameController: _nicknameController,
              consentTerms: _consentTerms,
              consentPrivacy: _consentPrivacy,
              ageOver14: _ageOver14,
              marketingConsent: _marketingConsent,
              busy: _busy,
              errorText: _errorText,
              onTermsChanged: (v) => setState(() => _consentTerms = v),
              onPrivacyChanged: (v) => setState(() => _consentPrivacy = v),
              onAgeChanged: (v) => setState(() => _ageOver14 = v),
              onMarketingChanged: (v) => setState(() => _marketingConsent = v),
              onSubmit: _signup,
            ),
            _LoginStep.verificationSent => _VerificationSentView(
              devToken: _verificationToken,
              busy: _busy,
              errorText: _errorText,
              onConfirm: _confirmVerification,
              onBackToLogin: _back,
            ),
          },
        ),
      ),
    );
  }
}

/// Step 1 — email + password sign-in.
class _LoginStepView extends StatelessWidget {
  const _LoginStepView({
    required this.emailController,
    required this.passwordController,
    required this.busy,
    required this.errorText,
    required this.onSubmit,
    required this.onSignup,
    required this.onGuest,
  });

  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool busy;
  final String? errorText;
  final VoidCallback onSubmit;
  final VoidCallback onSignup;
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
                '이메일로 시작하기',
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                '가입한 이메일과 비밀번호를 입력해 주세요. 소셜 로그인은 준비 중이에요.',
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  color: colors.ink600,
                ),
              ),
              const SizedBox(height: SpacingTokens.s6),
              AssenTextField(
                label: '이메일',
                controller: emailController,
                hintText: 'fan@assen.kr',
                keyboardType: TextInputType.emailAddress,
                prefixIcon: Icons.mail_outline,
              ),
              const SizedBox(height: SpacingTokens.s4),
              AssenTextField(
                label: '비밀번호',
                controller: passwordController,
                obscureText: true,
                errorText: errorText,
                prefixIcon: Icons.lock_outline,
              ),
              const SizedBox(height: SpacingTokens.s6),
              AssenButton(
                label: '로그인',
                expand: true,
                onPressed: busy ? null : onSubmit,
              ),
              const SizedBox(height: SpacingTokens.s2),
              AssenButton(
                label: '회원가입',
                style: AssenButtonStyle.ghost,
                expand: true,
                onPressed: busy ? null : onSignup,
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
/// tokens.md 2026-07-09 exception (login surface); it adds no logic to the auth
/// flow. The panel uses [AssenGradients.brandScrimmed] (not the plain
/// [AssenGradients.brand]) because it carries the tagline text, not just the
/// lockup graphic — the scrimmed variant keeps white body text ≥AA at every
/// point on the gradient (2026-07-10 a11y fix).
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
        gradient: AssenGradients.brandScrimmed,
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

/// Step 2 — register: email + password + nickname + required consent.
class _SignupStepView extends StatelessWidget {
  const _SignupStepView({
    required this.emailController,
    required this.passwordController,
    required this.nicknameController,
    required this.consentTerms,
    required this.consentPrivacy,
    required this.ageOver14,
    required this.marketingConsent,
    required this.busy,
    required this.errorText,
    required this.onTermsChanged,
    required this.onPrivacyChanged,
    required this.onAgeChanged,
    required this.onMarketingChanged,
    required this.onSubmit,
  });

  final TextEditingController emailController;
  final TextEditingController passwordController;
  final TextEditingController nicknameController;
  final bool consentTerms;
  final bool consentPrivacy;
  final bool ageOver14;
  final bool marketingConsent;
  final bool busy;
  final String? errorText;
  final ValueChanged<bool> onTermsChanged;
  final ValueChanged<bool> onPrivacyChanged;
  final ValueChanged<bool> onAgeChanged;
  final ValueChanged<bool> onMarketingChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '이메일로 가입하기',
          style: TextStyle(
            fontSize: TypographyTokens.headlineSize,
            fontWeight: FontWeight.w800,
            color: colors.ink900,
          ),
        ),
        const SizedBox(height: SpacingTokens.s2),
        Text(
          '가입 후 보내드리는 확인 메일의 링크로 인증을 마치면 로그인돼요.',
          style: TextStyle(
            fontSize: TypographyTokens.bodyMSize,
            color: colors.ink600,
          ),
        ),
        const SizedBox(height: SpacingTokens.s6),
        AssenTextField(
          label: '이메일',
          controller: emailController,
          hintText: 'fan@assen.kr',
          keyboardType: TextInputType.emailAddress,
          prefixIcon: Icons.mail_outline,
        ),
        const SizedBox(height: SpacingTokens.s4),
        AssenTextField(
          label: '비밀번호',
          controller: passwordController,
          obscureText: true,
          helperText: '8자 이상',
          prefixIcon: Icons.lock_outline,
        ),
        const SizedBox(height: SpacingTokens.s4),
        AssenTextField(
          label: '닉네임',
          controller: nicknameController,
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
          label: '개인정보 처리방침 동의',
          value: consentPrivacy,
          onChanged: onPrivacyChanged,
        ),
        AssenAgreementCell(
          label: '만 14세 이상입니다',
          value: ageOver14,
          onChanged: onAgeChanged,
        ),
        AssenAgreementCell(
          label: '마케팅 정보 수신 동의 (선택)',
          value: marketingConsent,
          onChanged: onMarketingChanged,
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

/// Step 3 — signup accepted: wait on the emailed verification link.
///
/// The real path ends here: the fan opens the link from their inbox on the web,
/// then returns and signs in. [devToken] is non-empty only against a dev/test
/// server, which echoes the token back so QA can close the loop in-app.
class _VerificationSentView extends StatelessWidget {
  const _VerificationSentView({
    required this.devToken,
    required this.busy,
    required this.errorText,
    required this.onConfirm,
    required this.onBackToLogin,
  });

  final String devToken;
  final bool busy;
  final String? errorText;
  final VoidCallback onConfirm;
  final VoidCallback onBackToLogin;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '확인 메일을 보냈어요',
          style: TextStyle(
            fontSize: TypographyTokens.headlineSize,
            fontWeight: FontWeight.w800,
            color: colors.ink900,
          ),
        ),
        const SizedBox(height: SpacingTokens.s2),
        Text(
          '받은 메일의 링크를 열어 인증을 완료해 주세요. 인증이 끝나면 로그인할 수 있어요.',
          style: TextStyle(
            fontSize: TypographyTokens.bodyMSize,
            color: colors.ink600,
          ),
        ),
        if (devToken.isNotEmpty) ...[
          const SizedBox(height: SpacingTokens.s4),
          // DEV/QA ONLY: a real server never echoes the token, so this branch is
          // unreachable outside dev/test (EMAIL_VERIFY_RETURN_TOKEN).
          const AssenNoticeBar(message: '개발용: 메일 없이 인증을 완료할 수 있어요.'),
          const SizedBox(height: SpacingTokens.s3),
          AssenButton(
            label: '인증 완료(개발용)',
            expand: true,
            onPressed: busy ? null : onConfirm,
          ),
        ],
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
          label: '로그인으로 돌아가기',
          style: AssenButtonStyle.ghost,
          expand: true,
          onPressed: busy ? null : onBackToLogin,
        ),
      ],
    );
  }
}
