// Tests for the creator follow action (M5 write wiring): the repository's
// follow/unfollow transport, the controller's optimistic follow (with reconcile
// + rollback), and the profile screen's auth-gated follow button. No network.

import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/creator/creator_controller.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/creator/creator_screen.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

import 'support/fakes.dart';
import 'support/recording_dio.dart';

Creator _creator() => const Creator(
  id: 'c1',
  handle: 'mio',
  displayName: '미오',
  followers: 100,
  posts: 12,
);

/// A creator repository whose follow result is configurable, so a test can
/// prove the controller reconciles against a differing server count (and rolls
/// back when [failWrites] is set).
class _WritableCreatorRepo implements CreatorRepository {
  _WritableCreatorRepo({
    required this.creator,
    this.followResult,
    this.failWrites = false,
  });

  final Creator creator;
  final FollowState? followResult;
  final bool failWrites;

  @override
  Future<Creator> fetchCreator(String handle) async => creator;

  @override
  Future<FollowState> setFollow(
    String handle, {
    required bool following,
  }) async {
    if (failWrites) throw Exception('boom');
    return followResult ?? (following: following, followers: creator.followers);
  }
}

/// An [AuthController] reporting a signed-in session so the profile shows the
/// follow button without the (deferred) real login.
class _AuthedController extends AuthController {
  @override
  AuthState build() =>
      const AuthState(isAuthenticated: true, accessToken: 'test-token');
}

Widget _host(CreatorRepository repo, {required bool signedIn}) => ProviderScope(
  overrides: [
    creatorRepositoryProvider.overrideWithValue(repo),
    membershipRepositoryProvider.overrideWithValue(
      FakeMembershipRepository(const []),
    ),
    if (signedIn) authControllerProvider.overrideWith(_AuthedController.new),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const CreatorScreen(handle: 'mio'),
  ),
);

void main() {
  group('CreatorRepository follow transport', () {
    test('setFollow(following: true) PUTs and parses the body', () async {
      final adapter = RecordingAdapter(
        body: {'following': true, 'followers': 42},
      );
      final repo = CreatorRepository(recordingDio(adapter));

      final result = await repo.setFollow('mio', following: true);

      expect(result, (following: true, followers: 42));
      expect(adapter.last.method, 'PUT');
      expect(adapter.last.path, '/api/creators/mio/follow');
    });

    test('setFollow(following: false) DELETEs the follow edge', () async {
      final adapter = RecordingAdapter(
        body: {'following': false, 'followers': 41},
      );
      final repo = CreatorRepository(recordingDio(adapter));

      final result = await repo.setFollow('mio', following: false);

      expect(result, (following: false, followers: 41));
      expect(adapter.last.method, 'DELETE');
    });

    test('setFollow translates a 404 into CreatorNotFoundException', () async {
      final adapter = RecordingAdapter(status: 404, body: {'detail': 'nope'});
      final repo = CreatorRepository(recordingDio(adapter));

      await expectLater(
        repo.setFollow('ghost', following: true),
        throwsA(isA<CreatorNotFoundException>()),
      );
    });
  });

  group('CreatorController.toggleFollow', () {
    test('applies the optimistic flip then reconciles', () async {
      final repo = _WritableCreatorRepo(
        creator: _creator(),
        // The server's authoritative count differs from the optimistic +1.
        followResult: (following: true, followers: 250),
      );
      final container = ProviderContainer(
        overrides: [creatorRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(creatorControllerProvider('mio').future);

      final future = container
          .read(creatorControllerProvider('mio').notifier)
          .toggleFollow();
      final optimistic = container
          .read(creatorControllerProvider('mio'))
          .value!;
      expect(optimistic.following, isTrue);
      expect(optimistic.followers, 101);

      await future;
      final reconciled = container
          .read(creatorControllerProvider('mio'))
          .value!;
      expect(reconciled.following, isTrue);
      expect(reconciled.followers, 250); // server truth wins
    });

    test('rolls back to the pre-toggle profile when the write fails', () async {
      final repo = _WritableCreatorRepo(
        creator: _creator(),
        failWrites: true,
      );
      final container = ProviderContainer(
        overrides: [creatorRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(creatorControllerProvider('mio').future);

      await container
          .read(creatorControllerProvider('mio').notifier)
          .toggleFollow();

      final creator = container.read(creatorControllerProvider('mio')).value!;
      expect(creator.following, isFalse);
      expect(creator.followers, 100);
    });
  });

  group('CreatorScreen follow button', () {
    testWidgets('a signed-in fan sees the button and can follow', (
      tester,
    ) async {
      final repo = _WritableCreatorRepo(
        creator: _creator(),
        followResult: (following: true, followers: 101),
      );
      await tester.pumpWidget(_host(repo, signedIn: true));
      await tester.pump();
      await tester.pump();

      expect(find.text('팔로우'), findsOneWidget);
      await tester.tap(find.text('팔로우'));
      await tester.pump();
      // Optimistic flip: the button label switches to 팔로잉.
      expect(find.text('팔로잉'), findsOneWidget);
    });

    testWidgets('a guest sees no follow button', (tester) async {
      final repo = _WritableCreatorRepo(creator: _creator());
      await tester.pumpWidget(_host(repo, signedIn: false));
      await tester.pump();
      await tester.pump();

      expect(find.text('팔로우'), findsNothing);
      expect(find.text('팔로잉'), findsNothing);
    });
  });
}
