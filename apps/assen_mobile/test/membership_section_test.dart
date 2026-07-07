// Contract + render tests for the membership section: Tier.fromJson parses the
// TierOut shape, the section renders the creator's tiers (featured emphasised)
// with a disabled 구독 CTA, and an empty tier list hides the section. Fake
// repository, no network.

import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:assen_mobile/src/membership/membership_section.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A membership repository stand-in returning fixed tiers.
class _FakeMembershipRepository implements MembershipRepository {
  _FakeMembershipRepository(this._tiers);

  final List<Tier> _tiers;

  @override
  Future<List<Tier>> fetchTiers(String creatorId) async => _tiers;
}

Map<String, dynamic> _tierRow() => {
  'id': 't1',
  'creator_id': 'c1',
  'name': '하츠코이',
  'price': 9900,
  'period': '월',
  'benefits': ['비공개 포스트', '전용 뱃지'],
  'badge': 'VIP',
  'featured': true,
  'sort_order': 0,
};

Widget _host(MembershipRepository repo) => ProviderScope(
  overrides: [membershipRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const Scaffold(body: MembershipSection(creatorId: 'c1')),
  ),
);

void main() {
  test('Tier.fromJson parses the TierOut shape', () {
    final tier = Tier.fromJson(_tierRow());
    expect(tier.name, '하츠코이');
    expect(tier.price, 9900);
    expect(tier.period, '월');
    expect(tier.benefits, ['비공개 포스트', '전용 뱃지']);
    expect(tier.featured, isTrue);
    expect(tier.pricePeriodLabel, '₩9,900 / 월');
  });

  testWidgets('renders the tier list with benefits', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeMembershipRepository([Tier.fromJson(_tierRow())]),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('멤버십'), findsOneWidget);
    expect(find.text('하츠코이'), findsOneWidget);
    expect(find.text('₩9,900 / 월'), findsOneWidget);
    expect(find.text('비공개 포스트'), findsOneWidget);
    expect(find.text('추천'), findsOneWidget); // featured badge
  });

  testWidgets('the 구독 CTA is shown disabled (payment gate)', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeMembershipRepository([Tier.fromJson(_tierRow())]),
      ),
    );
    await tester.pump();
    await tester.pump();

    final button = tester.widget<AssenButton>(
      find.widgetWithText(AssenButton, '구독'),
    );
    expect(button.onPressed, isNull); // disabled — no live subscribe
  });

  testWidgets('hides the section when the creator offers no tiers', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeMembershipRepository(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('멤버십'), findsNothing);
  });
}
