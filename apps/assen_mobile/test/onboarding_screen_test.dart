// Render tests for the 온보딩 screen: the intro slides render and the final slide
// carries only a DISABLED 약관·본인인증 card. The screen is hosted with NO provider
// overrides because it owns no repository — there is nothing that could call a
// consent/verify endpoint or persist an agreement (法務 gate). The consent
// button has no handler, proving no such action is wired.

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
    // The consent card lives on the final slide only — not shown at the start.
    expect(find.text('약관 동의 및 본인인증 (준비 중)'), findsNothing);
  });

  testWidgets('the final slide shows a disabled, inert consent card', (
    tester,
  ) async {
    await tester.pumpWidget(_host());
    await tester.pump();

    // Advance to the last slide via the (router-free) "다음" button. The final
    // CTA is never tapped, so no navigation/consent side effect is triggered.
    for (var i = 0; i < 3; i++) {
      await tester.tap(find.text('다음'));
      await tester.pumpAndSettle();
    }

    expect(find.text('둘러보기 시작'), findsOneWidget);
    expect(find.textContaining('약관 동의와 본인인증은 서비스 준비 중'), findsOneWidget);

    // The consent action is inert: no handler → no consent/verify call, no
    // stored agreement (法務 gate).
    final consentButton = tester.widget<AssenButton>(
      find.widgetWithText(AssenButton, '약관 동의 및 본인인증 (준비 중)'),
    );
    expect(consentButton.onPressed, isNull);
  });
}
