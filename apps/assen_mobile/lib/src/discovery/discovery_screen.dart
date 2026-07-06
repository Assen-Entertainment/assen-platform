import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_controller.dart';
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
        data: (creators) => creators.isEmpty
            ? AssenEmptyState(
                title: '아직 크리에이터가 없어요',
                message: '곧 새로운 크리에이터가 이곳에 소개됩니다.',
                actionLabel: '새로고침',
                onAction: () =>
                    ref.read(discoveryControllerProvider.notifier).refresh(),
              )
            : _CreatorList(creators: creators),
      ),
    );
  }
}

/// The loaded feed: a tappable list of creators.
class _CreatorList extends StatelessWidget {
  const _CreatorList({required this.creators});

  final List<Creator> creators;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
      itemCount: creators.length,
      itemBuilder: (context, index) {
        final creator = creators[index];
        return AssenListItem(
          title: creator.displayName,
          subtitle:
              '@${creator.handle}'
              '${creator.tagline == null ? '' : ' · ${creator.tagline}'}',
          leading: AssenAvatar(
            name: creator.displayName,
            isOnline: creator.isLive,
          ),
          onTap: () => context.go(RoutePaths.creator(creator.handle)),
        );
      },
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
