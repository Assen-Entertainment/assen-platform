import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/membership/subscription.dart';
import 'package:assen_mobile/src/membership/subscriptions_controller.dart';
import 'package:assen_mobile/src/membership/subscriptions_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 내 구독 (subscriptions) screen: the fan's active/past memberships.
///
/// Wired to `GET /api/subscriptions` through [subscriptionsControllerProvider].
/// Each card shows the creator, tier, price/period, status (이용중·해지 예정·만료)
/// and — for a paid membership — the next 결제일; a free membership hides billing
/// (ASS-297). Tapping a card opens the creator. Read-only — subscribe/cancel are
/// payment gates. A 401 renders "로그인이 필요해요"; other failures fall back to
/// [AssenErrorState] with retry.
class SubscriptionsScreen extends ConsumerWidget {
  /// Creates the subscriptions screen.
  const SubscriptionsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.mypage);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subscriptions = ref.watch(subscriptionsControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '내 구독', onBack: () => _back(context)),
      body: AssenAsyncView<List<Subscription>>(
        value: subscriptions,
        loading: const _SubscriptionsSkeleton(),
        onRetry: () =>
            ref.read(subscriptionsControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => error is SubscriptionsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '구독 내역을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : null,
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '구독 중인 멤버십이 없어요',
          message: '크리에이터의 멤버십에 가입하면 여기에서 관리할 수 있어요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(subscriptionsControllerProvider.notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s3),
            itemBuilder: (context, index) =>
                _SubscriptionCard(subscription: items[index]),
          ),
        ),
      ),
    );
  }
}

/// One subscription: creator + tier over price/period, status and next 결제일.
class _SubscriptionCard extends StatelessWidget {
  const _SubscriptionCard({required this.subscription});

  final Subscription subscription;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final billing = subscription.nextBillingDate;
    final handle = subscription.creatorHandle;
    return AssenCard(
      onTap: handle.isEmpty
          ? null
          : () => context.push(RoutePaths.creator(handle)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  subscription.creatorName,
                  style: TextStyle(
                    fontSize: TypographyTokens.titleMSize,
                    fontWeight: FontWeight.w700,
                    color: colors.ink900,
                  ),
                ),
              ),
              AssenStatusBadge(
                kind: _statusKind(subscription),
                label: subscription.statusLabel,
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            subscription.tierName,
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink600,
            ),
          ),
          const SizedBox(height: SpacingTokens.s3),
          Row(
            children: [
              Text(
                subscription.priceLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              if (!subscription.isFree && billing != null) ...[
                const Spacer(),
                Text(
                  '다음 결제 ${_ymd(billing)}',
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// Formats a date as `YYYY.MM.DD` for the next-billing anchor.
String _ymd(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}.$month.$day';
}

/// Maps a subscription state to the badge hue (해지 예정 reads as caution).
AssenStatusKind _statusKind(Subscription subscription) {
  if (subscription.cancelScheduled && subscription.status == 'active') {
    return AssenStatusKind.pending;
  }
  return switch (subscription.status) {
    'active' => AssenStatusKind.confirmed,
    'expired' || 'cancelled' => AssenStatusKind.cancelled,
    _ => AssenStatusKind.done,
  };
}

/// The loading state: skeleton subscription cards.
class _SubscriptionsSkeleton extends StatelessWidget {
  const _SubscriptionsSkeleton();

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
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: 80),
          ],
        ),
      ),
    );
  }
}
