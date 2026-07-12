// Render + toggle tests for the 알림 설정 (marketing consent) screen: a 401 shows
// the login prompt, a loaded consent renders the three per-channel toggles, and
// flipping a channel PUTs the full desired state (mocked). No network.

import 'package:assen_mobile/src/settings/marketing_consent.dart';
import 'package:assen_mobile/src/settings/marketing_repository.dart';
import 'package:assen_mobile/src/settings/notification_settings_screen.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed consent (or the 401 error) and keeps
/// the last saved consent so the toggle test can assert the PUT payload.
class _FakeMarketingRepository implements MarketingRepository {
  _FakeMarketingRepository(MarketingConsent consent) : _consent = consent;
  _FakeMarketingRepository.authRequired() : _consent = null;

  MarketingConsent? _consent;

  /// The consent passed to the last [saveConsent] call, or null if none.
  MarketingConsent? savedConsent;

  @override
  Future<MarketingConsent> fetchConsent() async {
    final consent = _consent;
    if (consent == null) throw const SettingsAuthRequiredException();
    return consent;
  }

  @override
  Future<MarketingConsent> saveConsent(MarketingConsent consent) async {
    savedConsent = consent;
    _consent = consent;
    return consent;
  }
}

Widget _host(MarketingRepository repository) => ProviderScope(
  overrides: [marketingRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const NotificationSettingsScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeMarketingRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('renders the three per-channel toggles', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeMarketingRepository(
          const MarketingConsent(push: true, sms: false, email: false),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('앱 푸시 알림'), findsOneWidget);
    expect(find.text('문자(SMS)'), findsOneWidget);
    expect(find.text('이메일'), findsOneWidget);
    // push + sms + email switches (email disabled, still rendered).
    expect(find.byType(Switch), findsNWidgets(3));
  });

  testWidgets('toggling push PUTs the full desired consent', (tester) async {
    final repo = _FakeMarketingRepository(
      const MarketingConsent(push: false, sms: false, email: false),
    );
    await tester.pumpWidget(_host(repo));
    await tester.pump();
    await tester.pump();

    // The first switch is the 앱 푸시 알림 toggle.
    await tester.tap(find.byType(Switch).first);
    await tester.pumpAndSettle();

    expect(repo.savedConsent?.push, true);
    expect(repo.savedConsent?.sms, false);
  });
}
