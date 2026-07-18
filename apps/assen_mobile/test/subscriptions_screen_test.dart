// Render tests for the 내 구독 (subscriptions) screen: a 401 shows the login
// prompt, an empty list shows the empty state, and a loaded list renders each
// subscription's creator, tier, price, status and 결제일. No network.

import 'package:assen_mobile/src/membership/subscription.dart';
import 'package:assen_mobile/src/membership/subscriptions_repository.dart';
import 'package:assen_mobile/src/membership/subscriptions_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed subscription list or the 401 error.
class _FakeSubscriptionsRepository implements SubscriptionsRepository {
  _FakeSubscriptionsRepository(List<Subscription> subs) : _subs = subs;
  _FakeSubscriptionsRepository.authRequired() : _subs = null;

  final List<Subscription>? _subs;

  @override
  Future<List<Subscription>> fetchSubscriptions() async {
    final subs = _subs;
    if (subs == null) throw const SubscriptionsAuthRequiredException();
    return subs;
  }
}

Subscription _paidSub() => Subscription(
  id: 's-1',
  creatorName: '미아',
  creatorHandle: 'mia',
  tierName: '골드 멤버십',
  price: 9900,
  period: 'monthly',
  status: 'active',
  cancelScheduled: false,
  isFree: false,
  nextBillingDate: DateTime(2026, 8),
);

Widget _host(SubscriptionsRepository repository) => ProviderScope(
  overrides: [
    subscriptionsRepositoryProvider.overrideWithValue(repository),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const SubscriptionsScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(
      _host(_FakeSubscriptionsRepository.authRequired()),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('an empty list shows the empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeSubscriptionsRepository(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('구독 중인 멤버십이 없어요'), findsOneWidget);
  });

  testWidgets('renders a paid subscription with its next billing date', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeSubscriptionsRepository([_paidSub()])));
    await tester.pump();
    await tester.pump();

    expect(find.text('미아'), findsOneWidget);
    expect(find.text('골드 멤버십'), findsOneWidget);
    expect(find.text('₩9,900'), findsOneWidget);
    expect(find.text('이용중'), findsOneWidget);
    expect(find.text('다음 결제 2026.08.01'), findsOneWidget);
  });
}
