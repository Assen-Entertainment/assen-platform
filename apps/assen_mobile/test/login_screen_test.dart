// Widget tests for the login screen: the phone step requests an OTP and
// advances to the code step (with the DEV-only mock OTP hint), a wrong code
// surfaces the error, and an unregistered number falls through to the signup
// step. Backed by a fake auth API + a no-op token store — no network, no
// platform channel, and no success-navigation (that needs a router; the
// controller test covers it).

import 'package:assen_mobile/src/auth/auth_api.dart';
import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:assen_mobile/src/login/login_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A fake auth API: OTP send always succeeds; login throws [loginError] if set.
class _FakeAuthApi implements AuthApi {
  _FakeAuthApi({this.loginError});

  final AuthException? loginError;
  int otpRequests = 0;

  @override
  Future<void> requestOtp(String phone) async => otpRequests++;

  @override
  Future<AuthTokens> login({
    required String phone,
    required String otp,
  }) async {
    final error = loginError;
    if (error != null) throw error;
    return const AuthTokens(accessToken: 'a', refreshToken: 'r');
  }

  @override
  Future<AuthTokens> signup({
    required String phone,
    required String otp,
    required String nickname,
    required bool consentTerms,
    required bool consentPrivacy,
  }) async => const AuthTokens(accessToken: 'a', refreshToken: 'r');

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

Widget _host(_FakeAuthApi api) => ProviderScope(
  overrides: [
    authApiProvider.overrideWithValue(api),
    tokenStoreProvider.overrideWithValue(_NoopTokenStore()),
  ],
  child: MaterialApp(theme: AssenTheme.light(), home: const LoginScreen()),
);

Future<void> _requestOtp(WidgetTester tester) async {
  await tester.enterText(find.byType(TextField), '01012345678');
  await tester.tap(find.text('인증번호 받기'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('requesting an OTP advances to the code step with a dev hint', (
    tester,
  ) async {
    final api = _FakeAuthApi();
    await tester.pumpWidget(_host(api));
    await tester.pump();

    expect(find.text('인증번호 받기'), findsOneWidget);

    await _requestOtp(tester);

    expect(api.otpRequests, 1);
    expect(find.text('인증번호 입력'), findsOneWidget);
    expect(find.text('로그인'), findsWidgets); // app-bar title + CTA
    // DEV-only: the deterministic mock code is hinted so the demo can proceed.
    expect(find.textContaining('개발용 인증번호'), findsOneWidget);
  });

  testWidgets('a wrong OTP shows the invalid-code error', (tester) async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.invalidOtp,
        '인증번호가 올바르지 않아요.',
      ),
    );
    await tester.pumpWidget(_host(api));
    await tester.pump();
    await _requestOtp(tester);

    await tester.enterText(find.byType(TextField), '000000');
    await tester.tap(find.widgetWithText(AssenButton, '로그인'));
    await tester.pumpAndSettle();

    expect(find.text('인증번호가 올바르지 않아요.'), findsOneWidget);
    // Still on the OTP step (not navigated, not advanced to signup).
    expect(find.text('가입하고 시작하기'), findsNothing);
  });

  testWidgets('an unregistered number advances to the signup step', (
    tester,
  ) async {
    final api = _FakeAuthApi(
      loginError: const AuthException(
        AuthFailureReason.accountNotRegistered,
        '가입이 필요해요.',
      ),
    );
    await tester.pumpWidget(_host(api));
    await tester.pump();
    await _requestOtp(tester);

    await tester.enterText(find.byType(TextField), '123456');
    await tester.tap(find.widgetWithText(AssenButton, '로그인'));
    await tester.pumpAndSettle();

    // The signup step is shown: nickname + required consent + the register CTA.
    expect(find.text('가입하고 시작하기'), findsOneWidget);
    expect(find.text('서비스 이용약관 동의'), findsOneWidget);
  });
}
