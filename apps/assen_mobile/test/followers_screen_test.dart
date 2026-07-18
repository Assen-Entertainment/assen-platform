// Render tests for the 팔로워 (followers) screen: a 404 shows the not-found
// state, an empty list shows the empty state, and a loaded list renders each
// follower — a creator follower shows their @handle, a plain fan shows 팬. No
// network.

import 'package:assen_mobile/src/followers/follower.dart';
import 'package:assen_mobile/src/followers/followers_repository.dart';
import 'package:assen_mobile/src/followers/followers_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed follower list, or the 404 error.
class _FakeFollowersRepository implements FollowersRepository {
  _FakeFollowersRepository(List<Follower> followers) : _followers = followers;
  _FakeFollowersRepository.notFound() : _followers = null;

  final List<Follower>? _followers;

  @override
  Future<List<Follower>> fetchFollowers(String handle) async {
    final followers = _followers;
    if (followers == null) throw const FollowersCreatorNotFoundException();
    return followers;
  }
}

const _followers = [
  Follower(id: 'f-1', nickname: '루나', isCreator: true, handle: 'luna'),
  Follower(id: 'f-2', nickname: '민지', isCreator: false),
];

Widget _host(FollowersRepository repository) => ProviderScope(
  overrides: [followersRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const FollowersScreen(handle: 'stellar'),
  ),
);

void main() {
  testWidgets('a 404 shows the not-found state', (tester) async {
    await tester.pumpWidget(_host(_FakeFollowersRepository.notFound()));
    await tester.pump();
    await tester.pump();

    expect(find.text('크리에이터를 찾을 수 없어요'), findsOneWidget);
  });

  testWidgets('an empty list shows the empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeFollowersRepository(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('아직 팔로워가 없어요'), findsOneWidget);
  });

  testWidgets('renders creator and fan followers distinctly', (tester) async {
    await tester.pumpWidget(_host(_FakeFollowersRepository(_followers)));
    await tester.pump();
    await tester.pump();

    expect(find.text('루나'), findsOneWidget);
    expect(find.text('@luna'), findsOneWidget); // creator follower link line
    expect(find.text('민지'), findsOneWidget);
    expect(find.text('팬'), findsOneWidget); // plain fan marker
  });
}
