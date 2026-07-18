// Render + unblock tests for the 차단 관리 (blocked creators) screen: a 401 shows
// the login prompt, an empty list shows the empty state, a loaded list renders
// each blocked creator, and 차단 해제 optimistically drops the row and DELETEs
// (mocked). No network.

import 'package:assen_mobile/src/settings/blocked_creator.dart';
import 'package:assen_mobile/src/settings/blocked_repository.dart';
import 'package:assen_mobile/src/settings/blocked_screen.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed block list (or the 401 error) and
/// records the ids passed to [unblock] so the unblock test can assert the call.
class _FakeBlockedRepository implements BlockedRepository {
  _FakeBlockedRepository(List<BlockedCreator> blocked)
    : _blocked = List.of(blocked);
  _FakeBlockedRepository.authRequired() : _blocked = null;

  final List<BlockedCreator>? _blocked;

  /// The creator ids passed to [unblock], in call order.
  final List<String> unblockedIds = [];

  @override
  Future<List<BlockedCreator>> fetchBlocked() async {
    final blocked = _blocked;
    if (blocked == null) throw const SettingsAuthRequiredException();
    return blocked;
  }

  @override
  Future<void> unblock(String creatorId) async => unblockedIds.add(creatorId);
}

Widget _host(BlockedRepository repository) => ProviderScope(
  overrides: [blockedRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(theme: AssenTheme.light(), home: const BlockedScreen()),
);

const _blocked = [
  BlockedCreator(creatorId: 'c-1', name: '미아', handle: 'mia'),
  BlockedCreator(creatorId: 'c-2', name: '루나', handle: 'luna'),
];

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeBlockedRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('an empty list shows the empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeBlockedRepository(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('차단한 크리에이터가 없어요'), findsOneWidget);
  });

  testWidgets('renders each blocked creator', (tester) async {
    await tester.pumpWidget(_host(_FakeBlockedRepository(_blocked)));
    await tester.pump();
    await tester.pump();

    expect(find.text('미아'), findsOneWidget);
    expect(find.text('@mia'), findsOneWidget);
    expect(find.text('루나'), findsOneWidget);
    expect(find.text('차단 해제'), findsNWidgets(2));
  });

  testWidgets('차단 해제 drops the row and DELETEs', (tester) async {
    final repo = _FakeBlockedRepository(_blocked);
    await tester.pumpWidget(_host(repo));
    await tester.pump();
    await tester.pump();

    // Unblock the first creator (미아).
    await tester.tap(find.text('차단 해제').first);
    await tester.pumpAndSettle();

    expect(repo.unblockedIds, ['c-1']);
    expect(find.text('미아'), findsNothing);
    expect(find.text('루나'), findsOneWidget);
  });
}
