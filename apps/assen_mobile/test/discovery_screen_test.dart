// Verifies the discovery (home) screen renders the ui_kit empty state when the
// feed comes back empty — while still exposing the 피드·스토어 browse shortcuts —
// exercising the AsyncNotifier -> ui_kit wiring in isolation (no router, no
// network).

import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in that reports an empty feed.
class _EmptyDiscoveryRepository implements DiscoveryRepository {
  @override
  Future<List<Creator>> fetchCreators() async => const [];
}

void main() {
  testWidgets('discovery shows the empty state for an empty feed', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          discoveryRepositoryProvider.overrideWithValue(
            _EmptyDiscoveryRepository(),
          ),
        ],
        child: MaterialApp(
          theme: AssenTheme.light(),
          home: const DiscoveryScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('아직 크리에이터가 없어요'), findsOneWidget);
    // The browse shortcuts stay reachable even with zero creators (IA gap fix).
    expect(find.text('피드'), findsOneWidget);
    expect(find.text('스토어'), findsOneWidget);
  });
}
