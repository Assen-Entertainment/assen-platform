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
/// feed is empty. The brand front is carried by the [AssenLogo] lockup in the
/// app bar and a single gradient hero band (the sanctioned tokens.md
/// exception), and the feed reveals in with a staggered [AssenReveal]
/// (reduced-motion safe).
class DiscoveryScreen extends ConsumerWidget {
  /// Creates the discovery screen.
  const DiscoveryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(discoveryControllerProvider);
    return Scaffold(
      // The brand lockup replaces the bare "둘러보기" title on the home bar
      // (mirroring the web shell's logo); the title stays as the a11y header.
      appBar: const AssenAppBar(
        title: '둘러보기',
        titleWidget: AssenLogo(size: AssenLogoSize.sm),
      ),
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
        // the empty feed, and after the hero in [_CreatorList] for the
        // populated feed.
        data: (creators) => creators.isEmpty
            ? Column(
                children: [
                  const AssenReveal(child: _DiscoveryHero()),
                  const AssenReveal(index: 1, child: _DiscoveryShortcuts()),
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

/// The loaded feed: a gradient brand hero + the browse shortcuts (피드 · 스토어)
/// over a tappable, staggered-in list of creators.
class _CreatorList extends StatelessWidget {
  const _CreatorList({required this.creators});

  final List<Creator> creators;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s2),
      // Index 0 is the hero, index 1 the shortcuts block; the rest are creators
      // (offset by two).
      itemCount: creators.length + 2,
      itemBuilder: (context, index) {
        if (index == 0) {
          return const AssenReveal(child: _DiscoveryHero());
        }
        if (index == 1) {
          return const AssenReveal(index: 1, child: _DiscoveryShortcuts());
        }
        final creator = creators[index - 2];
        return AssenReveal(
          index: index,
          child: AssenListItem(
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
          ),
        );
      },
    );
  }
}

/// The discovery brand hero — a single gradient welcome band.
///
/// The one discovery gradient moment sanctioned by the tokens.md 2026-07-09
/// exception (hero surface). White copy reads AA on the indigo→violet
/// [AssenGradients.brand] at every stop.
class _DiscoveryHero extends StatelessWidget {
  const _DiscoveryHero();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(
        SpacingTokens.s4,
        SpacingTokens.s4,
        SpacingTokens.s4,
        SpacingTokens.s2,
      ),
      padding: const EdgeInsets.all(SpacingTokens.s5),
      decoration: const BoxDecoration(
        gradient: AssenGradients.brand,
        borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.xl)),
        boxShadow: [
          BoxShadow(
            color: ElevationTokens.level1Color,
            offset: Offset(
              ElevationTokens.level1OffsetX,
              ElevationTokens.level1OffsetY,
            ),
            blurRadius: ElevationTokens.level1Blur,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '오늘도 최애를 응원해요',
            style: TypographyTokens.headline.copyWith(
              color: AssenGradients.onBrand,
            ),
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            '팔로우한 크리에이터의 새 소식과 스토어를 한곳에서 만나보세요.',
            style: TypographyTokens.bodyM.copyWith(
              color: AssenGradients.onBrand,
              height: 1.5,
            ),
          ),
        ],
      ),
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
            background: colors.indigo100,
            foreground: colors.indigoInk,
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
