import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_tier.dart';
import 'package:assen_mobile/src/studio/studio_tiers_controller.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 멤버십 관리 (studio tiers) screen: the creator owner's membership tiers.
///
/// Wired to `GET /api/studio/tiers` through [studioTiersControllerProvider] with
/// the same two unauthorised states as the studio dashboard — a 401 renders
/// "로그인이 필요해요", a 403 (signed-in non-owner) the "크리에이터 전용" notice. Each row
/// shows the tier's name, price/period, active-subscriber count (a count, never
/// revenue) and whether it is active/featured. Read-only — create/edit are
/// follow-up work.
class StudioTiersScreen extends ConsumerWidget {
  /// Creates the studio tiers screen.
  const StudioTiersScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.studio);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tiers = ref.watch(studioTiersControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '멤버십 관리', onBack: () => _back(context)),
      body: AssenAsyncView<List<StudioTier>>(
        value: tiers,
        loading: const _TiersSkeleton(),
        onRetry: () =>
            ref.read(studioTiersControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => switch (error) {
          StudioAuthRequiredException() => AssenEmptyState(
            title: '로그인이 필요해요',
            message: '멤버십을 관리하려면 먼저 로그인해 주세요.',
            actionLabel: '로그인',
            onAction: () => context.go(RoutePaths.login),
          ),
          StudioOwnerRequiredException() => const AssenEmptyState(
            title: '크리에이터 전용이에요',
            message: '멤버십 관리는 크리에이터 계정에서만 볼 수 있어요.',
          ),
          _ => null,
        },
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '등록한 멤버십이 없어요',
          message: '멤버십 티어를 만들면 여기에서 관리할 수 있어요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(studioTiersControllerProvider.notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s3),
            itemBuilder: (context, index) => _TierCard(tier: items[index]),
          ),
        ),
      ),
    );
  }
}

/// One tier: name + badges over price/period and subscriber count.
class _TierCard extends StatelessWidget {
  const _TierCard({required this.tier});

  final StudioTier tier;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  tier.name,
                  style: TextStyle(
                    fontSize: TypographyTokens.titleMSize,
                    fontWeight: FontWeight.w700,
                    color: colors.ink900,
                  ),
                ),
              ),
              if (tier.featured) ...[
                const AssenBadge(label: '추천', hue: AssenBadgeHue.lemon),
                const SizedBox(width: SpacingTokens.s2),
              ],
              AssenStatusBadge(
                kind: tier.active
                    ? AssenStatusKind.confirmed
                    : AssenStatusKind.pending,
                label: tier.active ? '활성' : '비활성',
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Row(
            children: [
              Text(
                tier.priceLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              const Spacer(),
              Text(
                '구독자 ${tier.subscribers}',
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

/// The loading state: skeleton tier cards.
class _TiersSkeleton extends StatelessWidget {
  const _TiersSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 3,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s3),
      itemBuilder: (context, index) => const AssenCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssenSkeleton(width: 140),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: 100),
          ],
        ),
      ),
    );
  }
}
