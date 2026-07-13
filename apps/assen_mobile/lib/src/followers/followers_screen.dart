import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/followers/follower.dart';
import 'package:assen_mobile/src/followers/followers_controller.dart';
import 'package:assen_mobile/src/followers/followers_repository.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 팔로워 (followers) screen: a creator's public followers, newest first.
///
/// Wired to `GET /api/creators/{handle}/followers` through
/// [followersControllerProvider] (keyed by handle). A public read — no login is
/// required. Each row shows the follower's nickname; a follower who operates a
/// creator shows their @handle + avatar and taps through to that profile. An
/// unknown handle renders "크리에이터를 찾을 수 없어요"; other failures fall back to
/// [AssenErrorState] with retry.
class FollowersScreen extends ConsumerWidget {
  /// Creates the followers screen for [handle].
  const FollowersScreen({required this.handle, super.key});

  /// The @-handle whose followers are listed.
  final String handle;

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.creator(handle));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final followers = ref.watch(followersControllerProvider(handle));
    return Scaffold(
      appBar: AssenAppBar(title: '팔로워', onBack: () => _back(context)),
      body: AssenAsyncView<List<Follower>>(
        value: followers,
        loading: const _FollowersSkeleton(),
        onRetry: () =>
            ref.read(followersControllerProvider(handle).notifier).refresh(),
        errorBuilder: (error, _) => error is FollowersCreatorNotFoundException
            ? const AssenEmptyState(
                title: '크리에이터를 찾을 수 없어요',
                message: '이미 삭제되었거나 존재하지 않는 크리에이터예요.',
              )
            : null,
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '아직 팔로워가 없어요',
          message: '이 크리에이터를 처음으로 팔로우해 보세요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(followersControllerProvider(handle).notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s2),
            itemBuilder: (context, index) =>
                _FollowerRow(follower: items[index]),
          ),
        ),
      ),
    );
  }
}

/// One follower: avatar + nickname over an optional @handle; taps to a creator.
class _FollowerRow extends StatelessWidget {
  const _FollowerRow({required this.follower});

  final Follower follower;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final handleLabel = follower.handleLabel;
    final canOpen = follower.isCreator && follower.handle.isNotEmpty;
    return AssenListItem(
      onTap: canOpen
          ? () => context.push(RoutePaths.creator(follower.handle))
          : null,
      showChevron: canOpen,
      leading: AssenAvatar(
        name: follower.nickname,
        imageProvider: follower.avatarUrl == null
            ? null
            : CachedNetworkImageProvider(follower.avatarUrl!),
        semanticLabel: '${follower.nickname} 프로필 사진',
      ),
      title: follower.nickname,
      subtitle: handleLabel.isEmpty ? null : handleLabel,
      trailing: canOpen
          ? null
          : Text(
              '팬',
              style: TextStyle(
                fontSize: TypographyTokens.bodySSize,
                color: colors.ink500,
              ),
            ),
    );
  }
}

/// The loading state: skeleton follower rows.
class _FollowersSkeleton extends StatelessWidget {
  const _FollowersSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 6,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s2),
      itemBuilder: (context, index) => const Row(
        children: [
          AssenSkeleton(width: 40, height: 40, radius: 20),
          SizedBox(width: SpacingTokens.s3),
          Expanded(child: AssenSkeleton(width: 120)),
        ],
      ),
    );
  }
}
