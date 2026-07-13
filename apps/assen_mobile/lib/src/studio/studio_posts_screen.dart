import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/now.dart';
import 'package:assen_mobile/src/common/relative_time.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/studio/studio_posts_controller.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 게시물 관리 (studio posts) screen: the creator owner's own posts.
///
/// Wired to `GET /api/studio/posts` through [studioPostsControllerProvider] with
/// the same two unauthorised states as the studio dashboard — a 401 renders
/// "로그인이 필요해요", a 403 (signed-in non-owner) the "크리에이터 전용" notice. Unlike the
/// public feed this includes the owner's 19+ posts (badged). Each row taps
/// through to the post detail; create/edit are follow-up work.
class StudioPostsScreen extends ConsumerWidget {
  /// Creates the studio posts screen.
  const StudioPostsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.studio);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posts = ref.watch(studioPostsControllerProvider);
    final now = ref.watch(nowProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '게시물 관리', onBack: () => _back(context)),
      body: AssenAsyncView<List<Post>>(
        value: posts,
        loading: const _PostsSkeleton(),
        onRetry: () =>
            ref.read(studioPostsControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => switch (error) {
          StudioAuthRequiredException() => AssenEmptyState(
            title: '로그인이 필요해요',
            message: '게시물을 관리하려면 먼저 로그인해 주세요.',
            actionLabel: '로그인',
            onAction: () => context.go(RoutePaths.login),
          ),
          StudioOwnerRequiredException() => const AssenEmptyState(
            title: '크리에이터 전용이에요',
            message: '게시물 관리는 크리에이터 계정에서만 볼 수 있어요.',
          ),
          _ => null,
        },
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '작성한 게시물이 없어요',
          message: '피드에 게시물을 올리면 여기에서 관리할 수 있어요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(studioPostsControllerProvider.notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s3),
            itemBuilder: (context, index) =>
                _PostCard(post: items[index], now: now),
          ),
        ),
      ),
    );
  }
}

/// One post: body preview over time, like/comment counts, 19+ badge.
class _PostCard extends StatelessWidget {
  const _PostCard({required this.post, required this.now});

  final Post post;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final body = post.body.isEmpty ? '(내용 없음)' : post.body;
    return AssenCard(
      onTap: () => context.push(RoutePaths.post(post.id)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                relativeTime(post.createdAt, now),
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink500,
                ),
              ),
              const Spacer(),
              if (post.isAdult)
                const AssenBadge(label: '19+', hue: AssenBadgeHue.peach),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            body,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink900,
            ),
          ),
          const SizedBox(height: SpacingTokens.s3),
          Row(
            children: [
              Icon(Icons.favorite_border, size: 16, color: colors.ink500),
              const SizedBox(width: SpacingTokens.s1),
              Text(
                '${post.likeCount}',
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink500,
                ),
              ),
              const SizedBox(width: SpacingTokens.s3),
              Icon(Icons.mode_comment_outlined, size: 16, color: colors.ink500),
              const SizedBox(width: SpacingTokens.s1),
              Text(
                '${post.commentCount}',
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// The loading state: skeleton post cards.
class _PostsSkeleton extends StatelessWidget {
  const _PostsSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 4,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s3),
      itemBuilder: (context, index) => const AssenCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssenSkeleton(width: 80),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: double.infinity),
            SizedBox(height: SpacingTokens.s2),
            AssenSkeleton(width: 120),
          ],
        ),
      ),
    );
  }
}
