import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/cached_media.dart';
import 'package:assen_mobile/src/common/now.dart';
import 'package:assen_mobile/src/common/relative_time.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/post/post_controller.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The post detail screen, reached from the feed via `/post/:id`.
///
/// Wired to `GET /api/posts/{id}` through [postControllerProvider]: it renders
/// the async states through ui_kit only — a skeleton while loading, a dedicated
/// "없는 게시물" state on 404 ([PostNotFoundException]) and [AssenErrorState]
/// (with retry) otherwise. On success it shows the post ([AssenPostCard]) and,
/// below it, the comment thread. Liking and commenting are auth-gated: a
/// signed-in fan gets a live like toggle (optimistic) and a comment composer,
/// while a guest keeps the login notice (a write would 401).
class PostScreen extends ConsumerWidget {
  /// Creates the detail screen for the post identified by [postId].
  const PostScreen({required this.postId, super.key});

  /// The post id from the route path parameter.
  final String postId;

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.feed);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final post = ref.watch(postControllerProvider(postId));
    final now = ref.watch(nowProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '게시물', onBack: () => _back(context)),
      body: AssenAsyncView<Post>(
        value: post,
        loading: const _PostSkeleton(),
        onRetry: () =>
            ref.read(postControllerProvider(postId).notifier).refresh(),
        // A 404 is a distinct "no such post" state with a feed CTA, not the
        // generic retry; anything else falls through (null) to the default.
        errorBuilder: (error, _) => error is PostNotFoundException
            ? AssenErrorState(
                title: '없는 게시물이에요',
                message: '게시물을 찾지 못했어요. 이미 삭제되었을 수 있어요.',
                retryLabel: '피드로',
                onRetry: () => context.go(RoutePaths.feed),
              )
            : null,
        data: (data) => _PostDetail(post: data, postId: postId, now: now),
      ),
    );
  }
}

/// The loaded detail: the post card, a gate notice, and the comment thread.
class _PostDetail extends ConsumerWidget {
  const _PostDetail({
    required this.post,
    required this.postId,
    required this.now,
  });

  final Post post;
  final String postId;
  final DateTime now;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final comments = ref.watch(postCommentsControllerProvider(postId));
    // Liking and commenting are auth-gated: a signed-in fan gets the live
    // controls, a guest keeps the login notice (the server would 401 a write).
    final signedIn = ref.watch(authControllerProvider).isAuthenticated;

    return ListView(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s8),
      children: [
        AssenPostCard(
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
          onLike: signedIn
              ? () => ref
                    .read(postControllerProvider(postId).notifier)
                    .toggleLike()
              : null,
        ),
        if (signedIn)
          _CommentComposer(postId: postId)
        else
          const Padding(
            padding: EdgeInsets.all(SpacingTokens.s4),
            child: AssenNoticeBar(
              message: '좋아요와 댓글은 로그인 후 이용할 수 있어요.',
            ),
          ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
          child: AssenSectionHeader(title: '댓글 ${post.commentCount}'),
        ),
        const SizedBox(height: SpacingTokens.s2),
        comments.when(
          loading: () => const _CommentsSkeleton(),
          error: (error, stackTrace) => const Padding(
            padding: EdgeInsets.all(SpacingTokens.s4),
            child: AssenNoticeBar(
              kind: AssenNoticeKind.warning,
              message: '댓글을 불러오지 못했어요.',
              icon: Icons.refresh,
            ),
          ),
          data: (items) => items.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(SpacingTokens.s6),
                  child: Text(
                    '아직 댓글이 없어요.',
                    textAlign: TextAlign.center,
                  ),
                )
              : Column(
                  children: [
                    for (final comment in items)
                      _CommentTile(comment: comment, now: now),
                  ],
                ),
        ),
      ],
    );
  }
}

/// The comment input shown to a signed-in fan under the post.
///
/// Owns the draft [TextEditingController] and an in-flight flag so the field
/// and 등록 button disable while a post is in progress. On success the notifier
/// appends the saved comment and the draft clears; on failure the draft is kept
/// and a snackbar invites a retry (commenting is not optimistic — a comment
/// carries a server-assigned id/author/timestamp).
class _CommentComposer extends ConsumerStatefulWidget {
  const _CommentComposer({required this.postId});

  final String postId;

  @override
  ConsumerState<_CommentComposer> createState() => _CommentComposerState();
}

class _CommentComposerState extends ConsumerState<_CommentComposer> {
  final _controller = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final body = _controller.text.trim();
    if (body.isEmpty || _submitting) return;
    setState(() => _submitting = true);
    try {
      await ref
          .read(postCommentsControllerProvider(widget.postId).notifier)
          .addComment(body);
      _controller.clear();
    } on Object {
      // Keep the draft and invite a retry rather than losing the fan's text.
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('댓글을 등록하지 못했어요. 잠시 후 다시 시도해 주세요.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      child: Row(
        children: [
          Expanded(
            child: AssenTextField(
              label: '댓글',
              hintText: '따뜻한 댓글을 남겨보세요',
              controller: _controller,
              enabled: !_submitting,
            ),
          ),
          const SizedBox(width: SpacingTokens.s3),
          AssenButton(
            label: '등록',
            onPressed: _submitting ? null : _submit,
          ),
        ],
      ),
    );
  }
}

/// One comment row: author + relative time over the body (read-only).
class _CommentTile extends StatelessWidget {
  const _CommentTile({required this.comment, required this.now});

  final Comment comment;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenAvatar(name: comment.author, size: AssenAvatarSize.s),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      comment.author,
                      style: TextStyle(
                        fontSize: TypographyTokens.bodySSize,
                        fontWeight: FontWeight.w600,
                        color: colors.ink900,
                      ),
                    ),
                    const SizedBox(width: SpacingTokens.s2),
                    Text(
                      relativeTime(comment.createdAt, now),
                      style: TextStyle(
                        fontSize: TypographyTokens.bodySSize,
                        color: colors.ink500,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  comment.body,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodyMSize,
                    height: 1.4,
                    color: colors.ink600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The comment-thread loading state: a few skeleton rows.
class _CommentsSkeleton extends StatelessWidget {
  const _CommentsSkeleton();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        3,
        (_) => const Padding(
          padding: EdgeInsets.symmetric(
            horizontal: SpacingTokens.s4,
            vertical: SpacingTokens.s3,
          ),
          child: Row(
            children: [
              AssenSkeleton(width: 32, height: 32, radius: 16),
              SizedBox(width: SpacingTokens.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AssenSkeleton(width: 100),
                    SizedBox(height: SpacingTokens.s2),
                    AssenSkeleton(width: double.infinity),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The post loading state: a header + body + media skeleton.
class _PostSkeleton extends StatelessWidget {
  const _PostSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: const [
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
        SizedBox(height: SpacingTokens.s4),
        AssenSkeleton(width: double.infinity),
        SizedBox(height: SpacingTokens.s2),
        AssenSkeleton(width: double.infinity),
        SizedBox(height: SpacingTokens.s4),
        AspectRatio(
          aspectRatio: 5 / 3,
          child: AssenSkeleton(
            width: double.infinity,
            height: double.infinity,
            radius: RadiusTokens.md,
          ),
        ),
      ],
    );
  }
}
