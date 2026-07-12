// Contract + render tests for the creator profile: Creator.fromJson parses the
// R8 profile fields, the screen renders a profile from a fake repository, and a
// 404 (CreatorNotFoundException) surfaces the "없는 크리에이터" state. No network.

import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/creator/creator_screen.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in that returns a fixed creator or throws not-found.
class _FakeCreatorRepository implements CreatorRepository {
  _FakeCreatorRepository.data(Creator creator)
    : _creator = creator,
      _error = null;
  _FakeCreatorRepository.notFound(String handle)
    : _creator = null,
      _error = CreatorNotFoundException(handle);

  final Creator? _creator;
  final Exception? _error;

  @override
  Future<Creator> fetchCreator(String handle) async {
    final error = _error;
    if (error != null) throw error;
    return _creator!;
  }

  @override
  Future<FollowState> setFollow(
    String handle, {
    required bool following,
  }) async => (following: following, followers: _creator?.followers ?? 0);
}

/// A membership repository stand-in reporting no tiers, so the profile's
/// membership section stays silent (and issues no network call) in these tests.
class _EmptyMembershipRepository implements MembershipRepository {
  @override
  Future<List<Tier>> fetchTiers(String creatorId) async => const [];
}

/// One full `CreatorOut` profile row as the server serializes it.
Map<String, dynamic> _profileRow() => {
  'id': 'a1b2',
  'handle': 'mio',
  'name': '미오',
  'bio': '버추얼 크리에이터입니다.',
  'accent_color': '#7C5CFF',
  'avatar_url': '',
  'cover_url': '',
  'category': '버추얼',
  'verified': true,
  'followers': 1284,
  'posts': 37,
  'following': true,
  'blocked': false,
};

Widget _host(Creator creator) => ProviderScope(
  overrides: [
    creatorRepositoryProvider.overrideWithValue(
      _FakeCreatorRepository.data(creator),
    ),
    membershipRepositoryProvider.overrideWithValue(
      _EmptyMembershipRepository(),
    ),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const CreatorScreen(handle: 'mio'),
  ),
);

void main() {
  test('Creator.fromJson parses the R8 profile fields', () {
    final creator = Creator.fromJson(_profileRow());
    expect(creator.displayName, '미오');
    expect(creator.bio, '버추얼 크리에이터입니다.');
    expect(creator.accentColor, '#7C5CFF');
    expect(creator.verified, isTrue);
    expect(creator.followers, 1284);
    expect(creator.posts, 37);
    expect(creator.following, isTrue);
    expect(creator.blocked, isFalse); // defaults false for a non-blocked row
    // Empty descriptors degrade to null.
    expect(creator.avatarUrl, isNull);
    expect(creator.coverUrl, isNull);
  });

  test('Creator.fromJson defaults the profile fields for a partial row', () {
    final creator = Creator.fromJson(const {'id': '1', 'handle': 'yuki'});
    expect(creator.displayName, 'yuki');
    expect(creator.verified, isFalse);
    expect(creator.followers, 0);
    expect(creator.posts, 0);
    expect(creator.bio, isNull);
  });

  testWidgets('renders the profile parsed from the server row', (tester) async {
    await tester.pumpWidget(_host(Creator.fromJson(_profileRow())));
    await tester.pump();
    await tester.pump();

    expect(find.text('미오'), findsOneWidget);
    expect(find.text('@mio · 버추얼'), findsOneWidget);
    expect(find.text('버추얼 크리에이터입니다.'), findsOneWidget);
    expect(find.text('1,284'), findsOneWidget); // grouped follower count
    expect(find.text('팔로워'), findsOneWidget);
    expect(find.byIcon(Icons.verified), findsOneWidget); // verified badge
  });

  testWidgets('a blocked creator shows the blocked state, not the profile', (
    tester,
  ) async {
    // The server returns the row (not a 404) with blocked=true when the caller
    // has personally blocked the creator; the screen must hide the profile.
    final creator = Creator.fromJson({..._profileRow(), 'blocked': true});
    await tester.pumpWidget(_host(creator));
    await tester.pump();
    await tester.pump();

    expect(find.text('차단한 크리에이터예요'), findsOneWidget);
    // Profile content is hidden.
    expect(find.text('버추얼 크리에이터입니다.'), findsNothing);
    expect(find.text('팔로워'), findsNothing);
  });

  testWidgets('a 404 shows the unknown-creator state', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          creatorRepositoryProvider.overrideWithValue(
            _FakeCreatorRepository.notFound('ghost'),
          ),
        ],
        child: MaterialApp(
          theme: AssenTheme.light(),
          home: const CreatorScreen(handle: 'ghost'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('없는 크리에이터예요'), findsOneWidget);
  });
}
