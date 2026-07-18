// Render + withdraw-confirm tests for the 계정 관리 (account) screen: a 401 shows
// the login prompt, a loaded profile renders the account info + 회원 탈퇴 action,
// and tapping 회원 탈퇴 opens the destructive confirm dialog. The irreversible
// withdrawal itself (signs out, routes to login) is not driven here; the test
// only asserts the confirm gate appears. No network.

import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/account_screen.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed profile (or the 401 error). The 탈퇴
/// action lives on AccountRepository and is not driven by these tests.
class _FakeSettingsRepository implements SettingsRepository {
  _FakeSettingsRepository(FanMe me) : _me = me;
  _FakeSettingsRepository.authRequired() : _me = null;

  final FanMe? _me;

  @override
  Future<FanMe> fetchMe() async {
    final me = _me;
    if (me == null) throw const SettingsAuthRequiredException();
    return me;
  }

  @override
  Future<FanMe> updateNickname(String nickname) async =>
      throw UnimplementedError();

  @override
  Future<VerifyResult> verifyAdult() async => throw UnimplementedError();
}

Widget _host(SettingsRepository repository) => ProviderScope(
  overrides: [settingsRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(theme: AssenTheme.light(), home: const AccountScreen()),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeSettingsRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('renders the account info and 회원 탈퇴 action', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeSettingsRepository(
          const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('계정 정보'), findsOneWidget);
    expect(find.text('민지'), findsOneWidget);
    expect(find.text('회원 탈퇴'), findsWidgets); // section header + button
  });

  testWidgets('tapping 회원 탈퇴 opens the destructive confirm dialog', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        _FakeSettingsRepository(
          const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.tap(find.widgetWithText(AssenButton, '회원 탈퇴'));
    await tester.pumpAndSettle();

    expect(find.text('정말 탈퇴하시겠어요?'), findsOneWidget);
    expect(find.text('탈퇴하기'), findsOneWidget); // the confirm CTA
    expect(find.text('취소'), findsOneWidget);
  });
}
