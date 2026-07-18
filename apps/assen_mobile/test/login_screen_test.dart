// Widget tests for the login screen: the email/password step signs in, a wrong
// credential and an unverified account surface their mapped errors, and the
// signup step captures the consents and lands on the "확인 메일을 보냈어요" state —
// where a dev/test server's echoed token exposes the "인증 완료(개발용)" affordance
// (absent on a real server, which returns ""). Backed by a fake auth API + a
// no-op token store behind a minimal GoRouter — no network, no platform
// channel.

import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:assen_mobile/src/login/login_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// A fake auth API: login throws [loginError] if set; signup echoes
/// [verificationToken] (as a dev/test server does) or throws [signupError].
class _FakeAuthApi implements AuthApi {
  _FakeAuthApi({
    this.loginError,
    this.signupError,
    this.verificationToken = '',
  });

  final AuthException? loginError;
  final AuthException? signupError;
  final String verificationToken;

  int signupCount = 0;
  String? verifiedToken;

  @override
  Future<AuthTokens> loginEmail({
    required String email,
    required String password,
  }) async {
    final error = loginError;
    if (error != null) throw error;
    return const AuthTokens(accessToken: 'a', refreshToken: 'r');
  }

  @override
  Future<String> signupEmail({
    required String email,
    required String password,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
    required bool ageOver14,
    bool marketingConsent = false,
  }) async {
    final error = signupError;
    if (error != null) throw error;
    signupCount++;
    return verificationToken;
  }

  @override
  Future<AuthTokens> verifyEmail(String token) async {
    verifiedToken = token;
    return const AuthTokens(accessToken: 'a', refreshToken: 'r');
  }

  @override
  Future<AuthTokens> refresh(String refreshToken) async =>
      throw UnimplementedError();

  @override
  Future<void> logout(String? accessToken) async {}
}

/// A token store that persists nothing (the screen only writes on success).
class _NoopTokenStore implements TokenStore {
  @override
  Future<AuthTokens?> read() async => null;

  @override
  Future<void> save(AuthTokens tokens) async {}

  @override
  Future<void> clear() async {}
}

/// Hosts the screen behind a minimal GoRouter, so the success path (which
/// routes to the post-login destination) is exercisable without the full app
/// router. The destinations are placeholders — only that we land there matters.
Widget _host(_FakeAuthApi api) => ProviderScope(
  overrides: [
    authApiProvider.overrideWithValue(api),
    tokenStoreProvider.overrideWithValue(_NoopTokenStore()),
  ],
  child: MaterialApp.router(
    theme: AssenTheme.light(),
    routerConfig: GoRouter(
      initialLocation: RoutePaths.login,
      routes: [
        GoRoute(
          path: RoutePaths.login,
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: RoutePaths.mypage,
          builder: (context, state) =>
              const Scaffold(body: Center(child: Text('마이 페이지'))),
        ),
        GoRoute(
          path: RoutePaths.discovery,
          builder: (context, state) =>
              const Scaffold(body: Center(child: Text('둘러보기'))),
        ),
      ],
    ),
  ),
);

/// Gives the test a tall surface so the whole signup step builds and is
/// tappable: the four consent cells and the CTA sit below a default 600px
/// viewport (the real screen scrolls). Mirrors the 설정 screen tests.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(400, 2000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// Fills the sign-in step's email + password and taps 로그인.
Future<void> _signIn(WidgetTester tester) async {
  await tester.enterText(
    find.widgetWithText(TextField, '이메일'),
    'fan@assen.test',
  );
  await tester.enterText(
    find.widgetWithText(TextField, '비밀번호'),
    'hunter2hunter2',
  );
  await tester.tap(find.widgetWithText(AssenButton, '로그인'));
  await tester.pumpAndSettle();
}

/// Opens the signup step and completes it with valid input + required consents.
Future<void> _signUp(WidgetTester tester) async {
  await tester.tap(find.widgetWithText(AssenButton, '회원가입'));
  await tester.pumpAndSettle();

  await tester.enterText(
    find.widgetWithText(TextField, '이메일'),
    'fan@assen.test',
  );
  await tester.enterText(
    find.widgetWithText(TextField, '비밀번호'),
    'hunter2hunter2',
  );
  await tester.enterText(find.widgetWithText(TextField, '닉네임'), '민지');
  for (final label in ['서비스 이용약관 동의', '개인정보 처리방침 동의', '만 14세 이상입니다']) {
    await tester.tap(find.text(label));
    await tester.pumpAndSettle();
  }
  await tester.tap(find.widgetWithText(AssenButton, '가입하고 시작하기'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the login wall opens on the email step', (tester) async {
    await tester.pumpWidget(_host(_FakeAuthApi()));
    await tester.pump();

    expect(find.text('이메일로 시작하기'), findsOneWidget);
    expect(find.widgetWithText(TextField, '이메일'), findsOneWidget);
    expect(find.widgetWithText(TextField, '비밀번호'), findsOneWidget);
    expect(find.widgetWithText(AssenButton, '로그인'), findsOneWidget);
  });

  testWidgets('a valid sign-in routes to the post-login destination', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeAuthApi()));
    await tester.pump();

    await _signIn(tester);

    expect(find.text('마이 페이지'), findsOneWidget);
  });

  testWidgets('a wrong credential shows the disclosure-safe error', (
    tester,
  ) async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.invalidCredentials,
        '이메일 또는 비밀번호가 올바르지 않아요.',
      ),
    );
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await _signIn(tester);

    expect(find.text('이메일 또는 비밀번호가 올바르지 않아요.'), findsOneWidget);
    // Still on the sign-in step (not navigated, not advanced to signup).
    expect(find.text('가입하고 시작하기'), findsNothing);
  });

  testWidgets('an unverified account is told to open its mail', (tester) async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.emailNotVerified,
        '이메일 인증이 필요해요. 받은 메일의 링크로 인증을 완료해 주세요.',
      ),
    );
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await _signIn(tester);

    expect(
      find.text('이메일 인증이 필요해요. 받은 메일의 링크로 인증을 완료해 주세요.'),
      findsOneWidget,
    );
  });

  testWidgets('the signup CTA opens the signup step with the consents', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeAuthApi()));
    await tester.pump();

    await tester.tap(find.widgetWithText(AssenButton, '회원가입'));
    await tester.pumpAndSettle();

    expect(find.text('이메일로 가입하기'), findsOneWidget);
    expect(find.text('서비스 이용약관 동의'), findsOneWidget);
    expect(find.text('개인정보 처리방침 동의'), findsOneWidget);
    expect(find.text('만 14세 이상입니다'), findsOneWidget);
    expect(find.text('가입하고 시작하기'), findsOneWidget);
  });

  testWidgets('signup without the required consents is refused locally', (
    tester,
  ) async {
    _useTallSurface(tester);
    final api = _FakeAuthApi();
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await tester.tap(find.widgetWithText(AssenButton, '회원가입'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextField, '이메일'),
      'fan@assen.test',
    );
    await tester.enterText(
      find.widgetWithText(TextField, '비밀번호'),
      'hunter2hunter2',
    );
    await tester.enterText(find.widgetWithText(TextField, '닉네임'), '민지');
    await tester.tap(find.widgetWithText(AssenButton, '가입하고 시작하기'));
    await tester.pumpAndSettle();

    expect(find.text('필수 약관에 모두 동의해 주세요.'), findsOneWidget);
    expect(api.signupCount, 0); // never reached the network
  });

  testWidgets('signup lands on the "확인 메일을 보냈어요" state', (tester) async {
    // A real server returns "" for the token, so no dev affordance is offered —
    // the fan must open the mailed link.
    _useTallSurface(tester);
    final api = _FakeAuthApi();
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await _signUp(tester);

    expect(api.signupCount, 1);
    expect(find.text('확인 메일을 보냈어요'), findsOneWidget);
    expect(find.text('인증 완료(개발용)'), findsNothing);
  });

  testWidgets('a dev-echoed token exposes the 인증 완료(개발용) affordance', (
    tester,
  ) async {
    _useTallSurface(tester);
    final api = _FakeAuthApi(verificationToken: 'verify-token-1');
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await _signUp(tester);
    expect(find.text('확인 메일을 보냈어요'), findsOneWidget);

    await tester.tap(find.widgetWithText(AssenButton, '인증 완료(개발용)'));
    await tester.pumpAndSettle();

    // The echoed token was handed straight to verify-email, which signs in and
    // routes to the post-login destination — no inbox needed.
    expect(api.verifiedToken, 'verify-token-1');
    expect(find.text('마이 페이지'), findsOneWidget);
  });

  testWidgets('an already-registered email drops back to sign-in', (
    tester,
  ) async {
    _useTallSurface(tester);
    final api = _FakeAuthApi(
      signupError: const AuthException(
        AuthFailureReason.emailAlreadyRegistered,
        '이미 가입된 이메일이에요. 로그인해 주세요.',
      ),
    );
    await tester.pumpWidget(_host(api));
    await tester.pump();

    await _signUp(tester);

    expect(find.text('이메일로 시작하기'), findsOneWidget); // back on the sign-in step
    expect(find.text('이미 가입된 이메일이에요. 로그인해 주세요.'), findsOneWidget);
  });
}
