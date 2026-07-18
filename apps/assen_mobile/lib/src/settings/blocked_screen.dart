import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/settings/blocked_controller.dart';
import 'package:assen_mobile/src/settings/blocked_creator.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 차단 관리 (blocked creators) screen: the fan's personal block list.
///
/// Wired to `GET /api/fan/blocks` (+ `DELETE .../{id}`) through
/// [blockedControllerProvider]. A personal block hides a creator from the fan's
/// own feed/discovery/search (ASS-226); this screen lists them and offers a
/// per-row 차단 해제. Unblock is optimistic, reverting with a toast on failure. A
/// 401 renders the shared "로그인이 필요해요" prompt; other failures fall back to
/// [AssenErrorState] with retry.
class BlockedScreen extends ConsumerWidget {
  /// Creates the blocked-creators screen.
  const BlockedScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.settings);
  }

  Future<void> _unblock(
    BuildContext context,
    WidgetRef ref,
    BlockedCreator creator,
  ) async {
    try {
      await ref
          .read(blockedControllerProvider.notifier)
          .unblock(
            creator.creatorId,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${creator.name} 님을 차단 해제했어요.')),
        );
      }
    } on SettingsAuthRequiredException {
      if (context.mounted) context.go(RoutePaths.login);
    } on Object {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('차단을 해제하지 못했어요. 다시 시도해 주세요.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final blocked = ref.watch(blockedControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '차단 관리', onBack: () => _back(context)),
      body: AssenAsyncView<List<BlockedCreator>>(
        value: blocked,
        loading: const _BlockedSkeleton(),
        onRetry: () => ref.read(blockedControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => error is SettingsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '차단 목록을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : null,
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '차단한 크리에이터가 없어요',
          message: '차단한 크리에이터는 내 피드·둘러보기·검색에서 숨겨져요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(blockedControllerProvider.notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s3),
            itemBuilder: (context, index) => _BlockedCard(
              creator: items[index],
              onUnblock: () => _unblock(context, ref, items[index]),
            ),
          ),
        ),
      ),
    );
  }
}

/// One blocked creator: identity + a 차단 해제 action.
class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.creator, required this.onUnblock});

  final BlockedCreator creator;
  final VoidCallback onUnblock;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return AssenCard(
      child: Row(
        children: [
          AssenAvatar(name: creator.name, semanticLabel: '${creator.name} 프로필'),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  creator.name,
                  style: TextStyle(
                    fontSize: TypographyTokens.titleMSize,
                    fontWeight: FontWeight.w600,
                    color: colors.ink900,
                  ),
                ),
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  '@${creator.handle}',
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: SpacingTokens.s3),
          AssenButton(
            label: '차단 해제',
            style: AssenButtonStyle.secondary,
            onPressed: onUnblock,
          ),
        ],
      ),
    );
  }
}

/// The loading state: skeleton blocked-creator rows.
class _BlockedSkeleton extends StatelessWidget {
  const _BlockedSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 4,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s3),
      itemBuilder: (context, index) => const AssenCard(
        child: Row(
          children: [
            AssenSkeleton(width: 40, height: 40, radius: 20),
            SizedBox(width: SpacingTokens.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AssenSkeleton(width: 120),
                  SizedBox(height: SpacingTokens.s2),
                  AssenSkeleton(width: 80),
                ],
              ),
            ),
            AssenSkeleton(width: 64, height: 32),
          ],
        ),
      ),
    );
  }
}
