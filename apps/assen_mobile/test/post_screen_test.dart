// Contract + render tests for the post detail: Post/Comment.fromJson parse the
// server shapes, the screen renders the post + read-only comments, a 404
// surfaces the "없는 게시물" state, and the write CTAs stay gated (no input field).

import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:assen_mobile/src/post/post_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A post repository stand-in returning a fixed post + comments, or a 404.
class _FakePostRepository implements PostRepository {
  _FakePostRepository.data(Post post, List<Comment> comments)
    : _post = post,
      _comments = comments,
      _notFound = false;
  _FakePostRepository.notFound()
    : _post = null,
      _comments = const [],
      _notFound = true;

  final Post? _post;
  final List<Comment> _comments;
  final bool _notFound;

  @override
  Future<Post> fetchPost(String postId) async {
    if (_notFound) throw PostNotFoundException(postId);
    return _post!;
  }

  @override
  Future<List<Comment>> fetchComments(String postId) async {
    if (_notFound) throw PostNotFoundException(postId);
    return _comments;
  }

  @override
  Future<LikeState> setLike(String postId, {required bool liked}) async {
    if (_notFound) throw PostNotFoundException(postId);
    return (liked: liked, likeCount: _post!.likeCount + (liked ? 1 : 0));
  }

  @override
  Future<Comment> addComment(String postId, String body) async {
    if (_notFound) throw PostNotFoundException(postId);
    return Comment(
      id: 'c-new',
      postId: postId,
      author: '나',
      body: body,
      createdAt: DateTime(2026, 7, 11),
    );
  }
}

Map<String, dynamic> _commentRow() => {
  'id': 'k1',
  'post_id': 'p1',
  'author': '유키',
  'body': '최고예요!',
  'created_at': '2026-07-02T00:00:00Z',
};

Post _post() => Post.fromJson(const {
  'id': 'p1',
  'creator_id': 'c1',
  'creator_name': '미오',
  'creator_handle': 'mio',
  'verified': false,
  'body': '오늘도 고마워요',
  'media_url': '',
  'like_count': 12,
  'comment_count': 1,
  'created_at': '2026-07-01T00:00:00Z',
});

Comment _comment() => Comment.fromJson(_commentRow());

Widget _host(PostRepository repo) => ProviderScope(
  overrides: [postRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const PostScreen(postId: 'p1'),
  ),
);

void main() {
  test('Post/Comment.fromJson parse the server shapes', () {
    expect(_post().body, '오늘도 고마워요');
    final comment = _comment();
    expect(comment.author, '유키');
    expect(comment.body, '최고예요!');
  });

  test('Comment.fromJson defaults a blank author to 익명', () {
    // An empty author is a valid value that displays as the server default.
    final comment = Comment.fromJson({..._commentRow(), 'author': ''});
    expect(comment.author, '익명');
  });

  test('Comment.fromJson throws when any required field is missing', () {
    for (final key in const [
      'id',
      'post_id',
      'author',
      'body',
      'created_at',
    ]) {
      final row = _commentRow()..remove(key);
      expect(
        () => Comment.fromJson(row),
        throwsA(isA<ArgumentError>()),
        reason: 'a missing "$key" must throw',
      );
    }
  });

  testWidgets('renders the post body and its comments', (tester) async {
    await tester.pumpWidget(
      _host(_FakePostRepository.data(_post(), [_comment()])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('오늘도 고마워요'), findsOneWidget); // post body
    expect(find.text('최고예요!'), findsOneWidget); // comment body
    expect(find.text('유키'), findsOneWidget); // comment author
  });

  testWidgets('keeps write actions gated (login notice, no comment field)', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(_FakePostRepository.data(_post(), [_comment()])),
    );
    await tester.pump();
    await tester.pump();

    // The interaction gate is stated, and there is no comment-writing input.
    expect(find.text('좋아요와 댓글은 로그인 후 이용할 수 있어요.'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('a 404 shows the unknown-post state', (tester) async {
    await tester.pumpWidget(_host(_FakePostRepository.notFound()));
    await tester.pump();
    await tester.pump();

    expect(find.text('없는 게시물이에요'), findsOneWidget);
  });
}
