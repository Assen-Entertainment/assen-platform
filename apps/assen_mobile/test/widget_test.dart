// Smoke tests for the assen_mobile shell: the router builds, the four-tab shell
// renders, and the home feed renders creators from a mock repository (no
// network). Goldens are out of scope here (human-gated, CONSTRAINTS #31).

import 'package:assen_mobile/src/app/app.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A repository stand-in returning fixed creators without touching the network.
class _FakeDiscoveryRepository implements DiscoveryRepository {
  _FakeDiscoveryRepository(this.creators);

  final List<Creator> creators;

  @override
  Future<List<Creator>> fetchCreators() async => creators;
}

const List<Creator> _twoCreators = [
  Creator(id: '1', handle: 'mio', displayName: '미오', tagline: '버추얼 크리에이터'),
  Creator(id: '2', handle: 'yuki', displayName: '유키', tagline: '게임 방송'),
];

void main() {
  testWidgets('router builds and the shell renders four tabs', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          discoveryRepositoryProvider.overrideWithValue(
            _FakeDiscoveryRepository(const []),
          ),
        ],
        child: const AssenApp(),
      ),
    );
    await tester.pump();

    expect(find.byType(BottomNavigationBar), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('검색'), findsOneWidget);
    expect(find.text('알림'), findsOneWidget);
    expect(find.text('마이'), findsOneWidget);
  });

  testWidgets('home renders the discovery list from the mock repository', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          discoveryRepositoryProvider.overrideWithValue(
            _FakeDiscoveryRepository(_twoCreators),
          ),
        ],
        child: const AssenApp(),
      ),
    );
    // First frame is the loading skeleton; a second pump lets the (resolved)
    // future rebuild the list. pumpAndSettle is avoided — the skeleton shimmer
    // never settles.
    await tester.pump();
    await tester.pump();

    expect(find.text('미오'), findsOneWidget);
    expect(find.text('유키'), findsOneWidget);
  });
}
