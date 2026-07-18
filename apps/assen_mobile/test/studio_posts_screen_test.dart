// Render tests for the 게시물 관리 (studio posts) screen: a 401 shows the login
// prompt, a 403 the creator-only notice, and a loaded list renders each post's
// body preview and like/comment counts. No network.

import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/studio/studio_posts_repository.dart';
import 'package:assen_mobile/src/studio/studio_posts_screen.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed post list, or the 401/403 errors.
class _FakeStudioPostsRepository implements StudioPostsRepository {
  _FakeStudioPostsRepository(List<Post> posts) : _posts = posts, _owner = false;
  _FakeStudioPostsRepository.authRequired() : _posts = null, _owner = false;
  _FakeStudioPostsRepository.ownerRequired() : _posts = null, _owner = true;

  final List<Post>? _posts;
  final bool _owner;

  @override
  Future<List<Post>> fetchPosts() async {
    if (_owner) throw const StudioOwnerRequiredException();
    final posts = _posts;
    if (posts == null) throw const StudioAuthRequiredException();
    return posts;
  }
}

Post _fixturePost() => Post(
  id: 'po-1',
  creatorId: 'c-1',
  creatorName: '미아',
  createdAt: DateTime(2026, 7, 10),
  body: '오늘의 소식이에요',
  likeCount: 3,
  commentCount: 1,
);

Widget _host(StudioPostsRepository repository) => ProviderScope(
  overrides: [studioPostsRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const StudioPostsScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeStudioPostsRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('a 403 shows the creator-only state', (tester) async {
    await tester.pumpWidget(_host(_FakeStudioPostsRepository.ownerRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('크리에이터 전용이에요'), findsOneWidget);
  });

  testWidgets('renders a post with its body and counts', (tester) async {
    await tester.pumpWidget(
      _host(_FakeStudioPostsRepository([_fixturePost()])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('오늘의 소식이에요'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
  });
}
