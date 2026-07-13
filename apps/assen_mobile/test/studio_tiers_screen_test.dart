// Render tests for the 멤버십 관리 (studio tiers) screen: a 401 shows the login
// prompt, a 403 the creator-only notice, and a loaded list renders each tier's
// name, price/period, active state and subscriber count. No network.

import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_tier.dart';
import 'package:assen_mobile/src/studio/studio_tiers_repository.dart';
import 'package:assen_mobile/src/studio/studio_tiers_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed tier list, or the 401/403 errors.
class _FakeStudioTiersRepository implements StudioTiersRepository {
  _FakeStudioTiersRepository(List<StudioTier> tiers)
    : _tiers = tiers,
      _owner = false;
  _FakeStudioTiersRepository.authRequired() : _tiers = null, _owner = false;
  _FakeStudioTiersRepository.ownerRequired() : _tiers = null, _owner = true;

  final List<StudioTier>? _tiers;
  final bool _owner;

  @override
  Future<List<StudioTier>> fetchTiers() async {
    if (_owner) throw const StudioOwnerRequiredException();
    final tiers = _tiers;
    if (tiers == null) throw const StudioAuthRequiredException();
    return tiers;
  }
}

const _tier = StudioTier(
  id: 't-1',
  name: '골드',
  price: 9900,
  period: '월',
  benefits: ['한정 굿즈'],
  active: true,
  subscribers: 5,
  featured: true,
  isFree: false,
);

Widget _host(StudioTiersRepository repository) => ProviderScope(
  overrides: [studioTiersRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const StudioTiersScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeStudioTiersRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('a 403 shows the creator-only state', (tester) async {
    await tester.pumpWidget(_host(_FakeStudioTiersRepository.ownerRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('크리에이터 전용이에요'), findsOneWidget);
  });

  testWidgets('renders a tier with its price, state and subscribers', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeStudioTiersRepository(const [_tier])));
    await tester.pump();
    await tester.pump();

    expect(find.text('골드'), findsOneWidget);
    expect(find.text('₩9,900 / 월'), findsOneWidget);
    expect(find.text('활성'), findsOneWidget);
    expect(find.text('구독자 5'), findsOneWidget);
    expect(find.text('추천'), findsOneWidget);
  });
}
