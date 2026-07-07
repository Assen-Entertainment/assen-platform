// Contract + render tests for the global feed: Post.fromJson parses the PostOut
// shape, and the screen renders data → empty → error through a fake repository
// (no network).

import 'package:assen_mobile/src/feed/feed_repository.dart';
import 'package:assen_mobile/src/feed/feed_screen.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A feed repository stand-in returning fixed posts or throwing.
class _FakeFeedRepository implements FeedRepository {
  _FakeFeedRepository.data(List<Post> posts) : _posts = posts, _error = null;
  _FakeFeedRepository.error() : _posts = null, _error = Exception('boom');

  final List<Post>? _posts;
  final Exception? _error;

  @override
  Future<List<Post>> fetchFeed() async {
    final error = _error;
    if (error != null) throw error;
    return _posts!;
  }
}

Map<String, dynamic> _postRow() => {
  'id': 'p1',
  'creator_id': 'c1',
  'creator_name': '미오',
  'creator_handle': 'mio',
  'verified': true,
  'body': '오늘 방송 고마웠어요!',
  'media_url': '',
  'like_count': 128,
  'comment_count': 16,
  'liked': false,
  'is_adult': false,
  'created_at': '2026-07-01T00:00:00Z',
};

Widget _host(FeedRepository repo) => ProviderScope(
  overrides: [feedRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(theme: AssenTheme.light(), home: const FeedScreen()),
);

void main() {
  test('Post.fromJson parses the PostOut shape', () {
    final post = Post.fromJson(_postRow());
    expect(post.id, 'p1');
    expect(post.creatorName, '미오');
    expect(post.creatorHandle, 'mio');
    expect(post.verified, isTrue);
    expect(post.likeCount, 128);
    expect(post.commentCount, 16);
    expect(post.mediaUrl, isNull); // empty media_url degrades to null
    expect(post.handleLabel, '@mio');
  });

  test('Post.fromJson throws when created_at is missing', () {
    expect(
      () => Post.fromJson(const {'id': 'p1'}),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('Post.fromJson falls back to the handle for a missing name', () {
    final post = Post.fromJson(const {
      'id': 'p1',
      'creator_handle': 'yuki',
      'created_at': '2026-07-01T00:00:00Z',
    });
    expect(post.creatorName, 'yuki');
  });

  testWidgets('renders a post parsed from the server row', (tester) async {
    await tester.pumpWidget(
      _host(_FakeFeedRepository.data([Post.fromJson(_postRow())])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('미오'), findsOneWidget);
    expect(find.text('오늘 방송 고마웠어요!'), findsOneWidget);
    expect(find.text('128'), findsOneWidget); // like count
    expect(find.text('16'), findsOneWidget); // comment count
  });

  testWidgets('shows the empty state for an empty feed', (tester) async {
    await tester.pumpWidget(_host(_FakeFeedRepository.data(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('아직 게시물이 없어요'), findsOneWidget);
  });

  testWidgets('shows the error state on failure', (tester) async {
    await tester.pumpWidget(_host(_FakeFeedRepository.error()));
    await tester.pump();
    await tester.pump();

    expect(find.text('불러오지 못했어요'), findsOneWidget);
  });
}
