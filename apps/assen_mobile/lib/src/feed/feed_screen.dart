import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/cached_media.dart';
import 'package:assen_mobile/src/common/now.dart';
import 'package:assen_mobile/src/common/relative_time.dart';
import 'package:assen_mobile/src/feed/feed_controller.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The global feed: the most recent posts across creators (`GET /api/feed`).
///
/// Reached from the discovery home shortcut. Wired to [feedControllerProvider]:
/// it renders the three async states through ui_kit only — post-card skeletons
/// while loading, [AssenErrorState] (with retry) on failure, an
/// [AssenEmptyState] for an empty feed, and otherwise a list of
/// [AssenPostCard]s. Tapping a card opens the post detail.
class FeedScreen extends ConsumerWidget {
  /// Creates the feed screen.
  const FeedScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.discovery);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(feedControllerProvider);
    final now = ref.watch(nowProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '피드', onBack: () => _back(context)),
      body: AssenAsyncView<List<Post>>(
        value: feed,
        loading: const _FeedSkeleton(),
        onRetry: () => ref.read(feedControllerProvider.notifier).refresh(),
        isEmpty: (posts) => posts.isEmpty,
        empty: () => AssenEmptyState(
          title: '아직 게시물이 없어요',
          message: '크리에이터가 새 소식을 올리면 이곳에 표시됩니다.',
          actionLabel: '새로고침',
          onAction: () => ref.read(feedControllerProvider.notifier).refresh(),
        ),
        data: (posts) => RefreshIndicator(
          onRefresh: () => ref.read(feedControllerProvider.notifier).refresh(),
          child: _FeedList(posts: posts, now: now),
        ),
      ),
    );
  }
}

/// The loaded feed: a list of tappable post cards, newest first.
class _FeedList extends StatelessWidget {
  const _FeedList({required this.posts, required this.now});

  final List<Post> posts;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      itemCount: posts.length,
      itemBuilder: (context, index) {
        final post = posts[index];
        return AssenPostCard(
          creatorName: post.creatorName,
          creatorMeta: post.handleLabel.isEmpty ? null : post.handleLabel,
          timeLabel: relativeTime(post.createdAt, now),
          verified: post.verified,
          avatar: AssenAvatar(name: post.creatorName),
          body: post.body,
          media: post.mediaUrl == null
              ? null
              : CachedMedia(url: post.mediaUrl!, semanticLabel: '게시물 이미지'),
          likeCount: post.likeCount,
          commentCount: post.commentCount,
          liked: post.liked,
          onTap: () => context.go(RoutePaths.post(post.id)),
        );
      },
    );
  }
}

/// The loading state: a few post-card skeletons standing in for the feed.
class _FeedSkeleton extends StatelessWidget {
  const _FeedSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: 4,
      itemBuilder: (context, index) => const Padding(
        padding: EdgeInsets.all(SpacingTokens.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                AssenSkeleton(width: 48, height: 48, radius: 24),
                SizedBox(width: SpacingTokens.s3),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      AssenSkeleton(width: 140),
                      SizedBox(height: SpacingTokens.s2),
                      AssenSkeleton(width: 100),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: double.infinity),
            SizedBox(height: SpacingTokens.s2),
            AssenSkeleton(width: double.infinity),
          ],
        ),
      ),
    );
  }
}
