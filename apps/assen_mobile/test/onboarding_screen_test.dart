// Render tests for the 온보딩 screen: the intro slides render and the final slide
// carries a live "로그인하고 시작하기" card that routes to the sign-in flow. The
// screen is hosted with NO provider overrides because it owns no repository —
// consent capture and 19+ 본인인증 happen in the login/settings flows, not here, so
// this screen still issues no consent/verify endpoint call of its own.

import 'package:assen_mobile/src/onboarding/onboarding_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host() =>
    MaterialApp(theme: AssenTheme.light(), home: const OnboardingScreen());

void main() {
  testWidgets('renders the first intro slide with no consent action yet', (
    tester,
  ) async {
    await tester.pumpWidget(_host());
    await tester.pump();

    expect(find.text('Assen에 오신 걸 환영해요'), findsOneWidget);
    expect(find.text('건너뛰기'), findsOneWidget);
    expect(find.text('다음'), findsOneWidget);
    // The login card lives on the final slide only — not shown at the start.
    expect(find.text('로그인하고 시작하기'), findsNothing);
  });

  testWidgets('the final slide shows a live login CTA', (tester) async {
    await tester.pumpWidget(_host());
    await tester.pump();

    // Advance to the last slide via the (router-free) "다음" button. The final
    // CTA is never tapped, so no navigation side effect is triggered here.
    for (var i = 0; i < 3; i++) {
      await tester.tap(find.text('다음'));
      await tester.pumpAndSettle();
    }

    expect(find.text('둘러보기 시작'), findsOneWidget);
    expect(find.textContaining('로그인 후 약관 동의와 본인인증'), findsOneWidget);

    // The card now routes to the sign-in flow: the CTA is live (has a handler);
    // consent/verify themselves still run in login/settings, never on this
    // screen.
    final loginButton = tester.widget<AssenButton>(
      find.widgetWithText(AssenButton, '로그인하고 시작하기'),
    );
    expect(loginButton.onPressed, isNotNull);
  });
}
