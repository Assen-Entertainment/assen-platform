import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_controller.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The home tab: the creator discovery feed.
///
/// The one screen wired to a real `api_client` call pattern
/// ([discoveryControllerProvider] → [DiscoveryController] → Dio). It renders
/// the three async states through ui_kit only — skeletons while loading,
/// [AssenErrorState] on failure (with retry), and [AssenEmptyState] when the
/// feed is empty — so no colour or layout is hard-coded here.
class DiscoveryScreen extends ConsumerWidget {
  /// Creates the discovery screen.
  const DiscoveryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(discoveryControllerProvider);
    return Scaffold(
      appBar: const AssenAppBar(title: '둘러보기'),
      body: feed.when(
        loading: () => const _DiscoverySkeleton(),
        error: (error, stackTrace) => AssenErrorState(
          title: '불러오지 못했어요',
          message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
          onRetry: () =>
              ref.read(discoveryControllerProvider.notifier).refresh(),
        ),
        // The 피드·스토어 shortcuts must stay reachable regardless of whether any
        // creators exist, so they are shown in both branches: inline here for
        // the empty feed, and at index 0 of [_CreatorList] for the populated
        // feed.
        data: (creators) => creators.isEmpty
            ? Column(
                children: [
                  const _DiscoveryShortcuts(),
                  Expanded(
                    child: AssenEmptyState(
                      title: '아직 크리에이터가 없어요',
                      message: '곧 새로운 크리에이터가 이곳에 소개됩니다.',
                      actionLabel: '새로고침',
                      onAction: () => ref
                          .read(discoveryControllerProvider.notifier)
                          .refresh(),
                    ),
                  ),
                ],
              )
            : _CreatorList(creators: creators),
      ),
    );
  }
}

/// The loaded feed: the browse shortcuts (피드 · 스토어) over a tappable list of
/// creators.
class _CreatorList extends StatelessWidget {
  const _CreatorList({required this.creators});

  final List<Creator> creators;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
      // Index 0 is the shortcuts block; the rest are creators (offset by one).
      itemCount: creators.length + 1,
      itemBuilder: (context, index) {
        if (index == 0) return const _DiscoveryShortcuts();
        final creator = creators[index - 1];
        return AssenListItem(
          title: creator.displayName,
          subtitle:
              '@${creator.handle}'
              '${creator.category == null ? '' : ' · ${creator.category}'}',
          leading: AssenAvatar(
            name: creator.displayName,
            imageProvider: creator.avatarUrl == null
                ? null
                : CachedNetworkImageProvider(creator.avatarUrl!),
            semanticLabel: '${creator.displayName} 프로필 사진',
          ),
          onTap: () => context.go(RoutePaths.creator(creator.handle)),
        );
      },
    );
  }
}

/// The discovery entry points into the global feed and store.
class _DiscoveryShortcuts extends StatelessWidget {
  const _DiscoveryShortcuts();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      children: [
        AssenListItem(
          title: '피드',
          subtitle: '크리에이터 소식 모아보기',
          leading: _ShortcutIcon(
            icon: Icons.dynamic_feed_outlined,
            background: colors.strawberryBg,
            foreground: colors.strawberryInk,
          ),
          onTap: () => context.go(RoutePaths.feed),
        ),
        AssenListItem(
          title: '스토어',
          subtitle: '상품 둘러보기',
          leading: _ShortcutIcon(
            icon: Icons.storefront_outlined,
            background: colors.skyBg,
            foreground: colors.skyInk,
          ),
          onTap: () => context.go(RoutePaths.store),
        ),
        const AssenDivider(),
      ],
    );
  }
}

/// A round pastel icon used as a shortcut row's leading slot.
class _ShortcutIcon extends StatelessWidget {
  const _ShortcutIcon({
    required this.icon,
    required this.background,
    required this.foreground,
  });

  final IconData icon;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: SpacingTokens.s12,
      height: SpacingTokens.s12,
      decoration: BoxDecoration(color: background, shape: BoxShape.circle),
      alignment: Alignment.center,
      child: Icon(icon, size: SpacingTokens.s6, color: foreground),
    );
  }
}

/// The loading state: a few skeleton rows standing in for the feed.
class _DiscoverySkeleton extends StatelessWidget {
  const _DiscoverySkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 6,
      itemBuilder: (context, index) => const Padding(
        padding: EdgeInsets.symmetric(vertical: SpacingTokens.s3),
        child: Row(
          children: [
            AssenSkeleton(width: 48, height: 48, radius: 24),
            SizedBox(width: SpacingTokens.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AssenSkeleton(width: 140),
                  SizedBox(height: SpacingTokens.s2),
                  AssenSkeleton(width: 200),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
