// Render + edit tests for the 설정 screen: a 401 shows the login prompt, a loaded
// profile renders the identity and the read-only 인증 badges, and editing the
// nickname PATCHes the server (mocked) and reflects the new value. 성인/KYC 인증 is
// display-only here (法務 gate) — no verify call is issued. No network.

import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:assen_mobile/src/settings/settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed profile (or the 401 error) and keeps
/// the nickname PATCH so the edit test can assert the request was made.
class _FakeSettingsRepository implements SettingsRepository {
  _FakeSettingsRepository(FanMe me, {this.updateThrowsAuth = false}) : _me = me;
  _FakeSettingsRepository.authRequired() : _me = null, updateThrowsAuth = false;

  FanMe? _me;

  /// When true, [updateNickname] throws as if the PATCH returned 401/403.
  final bool updateThrowsAuth;

  /// The nickname passed to the last [updateNickname] call, or null if none.
  String? patchedNickname;

  @override
  Future<FanMe> fetchMe() async {
    final me = _me;
    if (me == null) throw const SettingsAuthRequiredException();
    return me;
  }

  @override
  Future<FanMe> updateNickname(String nickname) async {
    if (updateThrowsAuth) throw const SettingsAuthRequiredException();
    patchedNickname = nickname;
    final current = _me!;
    final updated = FanMe(
      id: current.id,
      nickname: nickname,
      role: current.role,
      handle: current.handle,
      avatarUrl: current.avatarUrl,
      adultVerified: current.adultVerified,
      kycStatus: current.kycStatus,
    );
    _me = updated;
    return updated;
  }
}

Widget _host(SettingsRepository repository) => ProviderScope(
  overrides: [settingsRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(theme: AssenTheme.light(), home: const SettingsScreen()),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeSettingsRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget); // the CTA
  });

  testWidgets('renders the profile and read-only 인증 badges', (tester) async {
    // A tall surface so the whole settings ListView builds (the app-intro row
    // and sign-out sit below a default 600px test viewport).
    tester.view.physicalSize = const Size(400, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _host(
        _FakeSettingsRepository(
          const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('민지'), findsWidgets); // header + 닉네임 row subtitle
    expect(find.text('미인증'), findsWidgets); // 성인 + KYC badges (both unverified)
    expect(find.text('앱 소개 다시 보기'), findsOneWidget);
    expect(find.text('로그아웃'), findsOneWidget);
  });

  testWidgets('editing the nickname PATCHes and reflects the new value', (
    tester,
  ) async {
    final repo = _FakeSettingsRepository(
      const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
    );
    await tester.pumpWidget(_host(repo));
    await tester.pump();
    await tester.pump();

    // Open the nickname editor sheet from the 닉네임 row.
    await tester.tap(find.text('닉네임'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '지민');
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();

    // The PATCH carried the new nickname and the loaded profile reflects it.
    expect(repo.patchedNickname, '지민');
    expect(find.text('지민'), findsWidgets);
    expect(find.text('민지'), findsNothing);
  });

  testWidgets('a 401/403 on nickname save drops to the login-required state', (
    tester,
  ) async {
    // A session that expires mid-edit must not leave a stale, still-signed-in
    // profile behind a generic error — the screen drops to "로그인이 필요해요".
    tester.view.physicalSize = const Size(400, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final repo = _FakeSettingsRepository(
      const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
      updateThrowsAuth: true,
    );
    await tester.pumpWidget(_host(repo));
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('닉네임'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '지민');
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();

    // Login-required state shows; no generic inline error, no PATCH recorded.
    expect(find.text('로그인이 필요해요'), findsOneWidget);
    expect(find.text('닉네임을 변경하지 못했어요. 다시 시도해 주세요.'), findsNothing);
    expect(repo.patchedNickname, isNull);
  });
}
