// Contract + render tests for the 스튜디오 screen: StudioStats.fromJson parses the
// server StudioStatsOut shape, a 401 shows the login prompt, a 403 shows the
// distinct "크리에이터 전용" state, and a creator dashboard renders its six metrics.
// No network.

import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_screen.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in returning fixed stats or a typed auth/owner error.
class _FakeStudioRepository implements StudioRepository {
  _FakeStudioRepository.stats(StudioStats stats)
    : _stats = stats,
      _error = null;
  _FakeStudioRepository.authRequired()
    : _stats = null,
      _error = const StudioAuthRequiredException();
  _FakeStudioRepository.ownerRequired()
    : _stats = null,
      _error = const StudioOwnerRequiredException();

  final StudioStats? _stats;
  final Exception? _error;

  @override
  Future<StudioStats> fetchStats() async {
    final error = _error;
    if (error != null) throw error;
    return _stats!;
  }
}

Widget _host(StudioRepository repository) => ProviderScope(
  overrides: [studioRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(theme: AssenTheme.light(), home: const StudioScreen()),
);

void main() {
  test('StudioStats.fromJson parses the StudioStatsOut shape', () {
    final stats = StudioStats.fromJson(const {
      'followers': 1284,
      'posts': 42,
      'products': 8,
      'products_selling': 5,
      'orders': 17,
      'subscribers': 30,
    });
    expect(stats.followers, 1284);
    expect(stats.productsSelling, 5);
    expect(stats.subscribers, 30);
  });

  test('StudioStats.fromJson throws on a missing required field', () {
    // Every count is contract-required; a missing `subscribers` is field drift
    // and throws rather than silently defaulting to 0.
    expect(
      () => StudioStats.fromJson(const {
        'followers': 1,
        'posts': 1,
        'products': 1,
        'products_selling': 1,
        'orders': 1,
      }),
      throwsA(isA<ArgumentError>()),
    );
  });

  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeStudioRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget); // the CTA
  });

  testWidgets('a 403 shows the creator-only state, not the login prompt', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_FakeStudioRepository.ownerRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('크리에이터 전용이에요'), findsOneWidget);
    // The two unauthorized states are distinct — 403 is not the login prompt.
    expect(find.text('로그인이 필요해요'), findsNothing);
  });

  testWidgets('a creator dashboard renders its metrics', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeStudioRepository.stats(
          const StudioStats(
            followers: 1284,
            posts: 42,
            products: 8,
            productsSelling: 5,
            orders: 17,
            subscribers: 30,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('팔로워'), findsOneWidget);
    expect(find.text('1,284'), findsOneWidget); // formatted followers
    expect(find.text('구독자'), findsOneWidget);
  });
}
