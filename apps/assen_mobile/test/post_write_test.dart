// Tests for the post write actions (M5 write wiring): the repository's
// like/comment transport, the controller's optimistic like (with reconcile +
// rollback) and comment append (with the header count bump), and the post
// detail screen's auth-gated like button + comment composer. No network.

import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/post/post_controller.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:assen_mobile/src/post/post_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

import 'support/recording_dio.dart';

Post _post() => Post(
  id: 'p1',
  creatorId: 'c1',
  creatorName: '미오',
  createdAt: DateTime(2026, 7),
  creatorHandle: 'mio',
  body: '오늘도 고마워요',
  likeCount: 10,
  commentCount: 2,
);

/// A post repository whose write results are configurable, so a test can prove
/// the controller reconciles against a server value that differs from the
/// optimistic one (and rolls back when [failWrites] is set).
class _WritablePostRepo implements PostRepository {
  _WritablePostRepo({
    required this.post,
    this.comments = const [],
    this.likeResult,
    this.failWrites = false,
  });

  final Post post;
  final List<Comment> comments;
  final LikeState? likeResult;
  final bool failWrites;

  @override
  Future<Post> fetchPost(String postId) async => post;

  @override
  Future<List<Comment>> fetchComments(String postId) async => comments;

  @override
  Future<LikeState> setLike(String postId, {required bool liked}) async {
    if (failWrites) throw Exception('boom');
    return likeResult ?? (liked: liked, likeCount: post.likeCount);
  }

  @override
  Future<Comment> addComment(String postId, String body) async {
    if (failWrites) throw Exception('boom');
    return Comment(
      id: 'c-new',
      postId: postId,
      author: '나',
      body: body,
      createdAt: DateTime(2026, 7, 2),
    );
  }
}

/// An [AuthController] reporting a signed-in session so the post screen shows
/// the write controls without the (deferred) real login.
class _AuthedController extends AuthController {
  @override
  AuthState build() =>
      const AuthState(isAuthenticated: true, accessToken: 'test-token');
}

Widget _host(PostRepository repo, {required bool signedIn}) => ProviderScope(
  overrides: [
    postRepositoryProvider.overrideWithValue(repo),
    if (signedIn) authControllerProvider.overrideWith(_AuthedController.new),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const PostScreen(postId: 'p1'),
  ),
);

void main() {
  group('PostRepository write transport', () {
    test('setLike(liked: true) PUTs and parses the body', () async {
      final adapter = RecordingAdapter(body: {'liked': true, 'like_count': 13});
      final repo = PostRepository(recordingDio(adapter));

      final result = await repo.setLike('p1', liked: true);

      expect(result, (liked: true, likeCount: 13));
      expect(adapter.last.method, 'PUT');
      expect(adapter.last.path, '/api/posts/p1/like');
    });

    test('setLike(liked: false) DELETEs the like endpoint', () async {
      final adapter = RecordingAdapter(body: {'liked': false, 'like_count': 4});
      final repo = PostRepository(recordingDio(adapter));

      final result = await repo.setLike('p1', liked: false);

      expect(result, (liked: false, likeCount: 4));
      expect(adapter.last.method, 'DELETE');
    });

    test('setLike translates a 404 into PostNotFoundException', () async {
      final adapter = RecordingAdapter(status: 404, body: {'detail': 'nope'});
      final repo = PostRepository(recordingDio(adapter));

      await expectLater(
        repo.setLike('p1', liked: true),
        throwsA(isA<PostNotFoundException>()),
      );
    });

    test('addComment POSTs the body and parses the CommentOut', () async {
      final adapter = RecordingAdapter(
        status: 201,
        body: {
          'id': 'k1',
          'post_id': 'p1',
          'author': '유키',
          'body': '화이팅',
          'created_at': '2026-07-02T00:00:00Z',
        },
      );
      final repo = PostRepository(recordingDio(adapter));

      final comment = await repo.addComment('p1', '화이팅');

      expect(comment.author, '유키');
      expect(comment.body, '화이팅');
      expect(adapter.last.method, 'POST');
      expect(adapter.last.path, '/api/posts/p1/comments');
      expect(adapter.last.data, {'body': '화이팅'});
    });
  });

  group('PostController.toggleLike', () {
    test('applies the optimistic flip then reconciles', () async {
      final repo = _WritablePostRepo(
        post: _post(),
        // The server's authoritative count differs from the optimistic +1.
        likeResult: (liked: true, likeCount: 100),
      );
      final container = ProviderContainer(
        overrides: [postRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(postControllerProvider('p1').future);

      final future = container
          .read(postControllerProvider('p1').notifier)
          .toggleLike();
      // Optimistic step: applied synchronously, before the network await.
      final optimistic = container.read(postControllerProvider('p1')).value!;
      expect(optimistic.liked, isTrue);
      expect(optimistic.likeCount, 11);

      await future;
      final reconciled = container.read(postControllerProvider('p1')).value!;
      expect(reconciled.liked, isTrue);
      expect(reconciled.likeCount, 100); // server truth wins
    });

    test('rolls back to the pre-toggle post when the write fails', () async {
      final repo = _WritablePostRepo(
        post: _post(),
        failWrites: true,
      );
      final container = ProviderContainer(
        overrides: [postRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(postControllerProvider('p1').future);

      await container.read(postControllerProvider('p1').notifier).toggleLike();

      final post = container.read(postControllerProvider('p1')).value!;
      expect(post.liked, isFalse);
      expect(post.likeCount, 10);
    });
  });

  group('PostCommentsController.addComment', () {
    test('appends the comment and bumps the count', () async {
      final repo = _WritablePostRepo(
        post: _post(),
        comments: [
          Comment(
            id: 'k0',
            postId: 'p1',
            author: '유키',
            body: '첫 댓글',
            createdAt: DateTime(2026, 7),
          ),
        ],
      );
      final container = ProviderContainer(
        overrides: [postRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      // Load both the post (for the count bump) and the thread.
      await container.read(postControllerProvider('p1').future);
      await container.read(postCommentsControllerProvider('p1').future);

      await container
          .read(postCommentsControllerProvider('p1').notifier)
          .addComment('두 번째 댓글');

      final thread = container
          .read(postCommentsControllerProvider('p1'))
          .value!;
      expect(thread.length, 2);
      expect(thread.last.body, '두 번째 댓글');
      final post = container.read(postControllerProvider('p1')).value!;
      expect(post.commentCount, 3); // bumped from 2
    });

    test('propagates a failure so the composer can keep the draft', () async {
      final repo = _WritablePostRepo(post: _post(), failWrites: true);
      final container = ProviderContainer(
        overrides: [postRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      await container.read(postCommentsControllerProvider('p1').future);

      await expectLater(
        container
            .read(postCommentsControllerProvider('p1').notifier)
            .addComment('안녕'),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('PostScreen write controls', () {
    testWidgets('a signed-in fan can like (optimistic) and comment', (
      tester,
    ) async {
      final repo = _WritablePostRepo(
        post: _post(),
        likeResult: (liked: true, likeCount: 11),
      );
      await tester.pumpWidget(_host(repo, signedIn: true));
      await tester.pump();
      await tester.pump();

      // The like heart is a button; tapping it optimistically increments.
      expect(find.byIcon(Icons.favorite_border), findsOneWidget);
      await tester.tap(find.byIcon(Icons.favorite_border));
      await tester.pump();
      expect(find.byIcon(Icons.favorite), findsOneWidget);
      expect(find.text('11'), findsOneWidget);

      // The composer posts a comment that then appears in the thread.
      expect(find.byType(TextField), findsOneWidget);
      await tester.enterText(find.byType(TextField), '좋은 글이에요');
      await tester.tap(find.text('등록'));
      await tester.pumpAndSettle();
      expect(find.text('좋은 글이에요'), findsOneWidget);
    });

    testWidgets('a guest keeps the login notice and no composer', (
      tester,
    ) async {
      final repo = _WritablePostRepo(post: _post());
      await tester.pumpWidget(_host(repo, signedIn: false));
      await tester.pump();
      await tester.pump();

      expect(find.text('좋아요와 댓글은 로그인 후 이용할 수 있어요.'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
    });
  });
}
