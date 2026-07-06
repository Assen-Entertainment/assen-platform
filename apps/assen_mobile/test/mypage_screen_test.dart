// Contract + render tests for the 마이 tab: FanMe.fromJson parses the server
// shape and the screen renders the identity + a sign-out action from a fake
// repository. No network.

import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/mypage/mypage_repository.dart';
import 'package:assen_mobile/src/mypage/mypage_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in returning a fixed identity summary.
class _FakeMyPageRepository implements MyPageRepository {
  _FakeMyPageRepository(this._me);

  final FanMe _me;

  @override
  Future<FanMe> fetchMe() async => _me;
}

Widget _host(FanMe me) => ProviderScope(
  overrides: [
    myPageRepositoryProvider.overrideWithValue(_FakeMyPageRepository(me)),
  ],
  child: MaterialApp(theme: AssenTheme.light(), home: const MyPageScreen()),
);

void main() {
  test('FanMe.fromJson parses the FanMeOut shape', () {
    final me = FanMe.fromJson(const {
      'id': 'fan-1',
      'nickname': '민지',
      'role': 'fan',
      'handle': '',
      'avatar_url': '',
      'adult_verified': false,
      'kyc_status': 'unverified',
    });
    expect(me.nickname, '민지');
    expect(me.role, 'fan');
    expect(me.handle, isNull); // empty handle degrades to null
    expect(me.adultVerified, isFalse);
  });

  test('FanMe.fromJson throws on a missing required field', () {
    expect(
      () => FanMe.fromJson(const {'id': 'x', 'nickname': '민지'}),
      throwsA(isA<ArgumentError>()),
    );
  });

  testWidgets('renders the fan identity and a sign-out button', (tester) async {
    await tester.pumpWidget(
      _host(
        const FanMe(id: 'fan-1', nickname: '민지', role: 'fan'),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('민지'), findsOneWidget);
    expect(find.text('로그아웃'), findsOneWidget);
  });
}
