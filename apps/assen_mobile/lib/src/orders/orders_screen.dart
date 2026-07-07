import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/relative_time.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/orders_controller.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 주문 내역 (orders) screen: the signed-in fan's own orders, newest first.
///
/// Read-only — placement, cancellation and refund requests are payment/legal
/// gates and are deliberately not offered here. Wired to `GET /api/orders`
/// through [ordersControllerProvider]. Because the app ships signed-out, the
/// default path is a 401 → [OrdersAuthRequiredException], which this screen
/// renders as a "로그인이 필요해요" empty state (with a login CTA) rather than an
/// error. When authenticated it lists each order (status badge, contents,
/// total, relative time, and a refund badge when one exists); other failures
/// fall back to [AssenErrorState] with retry.
class OrdersScreen extends ConsumerWidget {
  /// Creates the orders screen.
  const OrdersScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.mypage);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orders = ref.watch(ordersControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '주문 내역', onBack: () => _back(context)),
      body: orders.when(
        loading: () => const _OrdersSkeleton(),
        error: (error, stackTrace) => error is OrdersAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '주문 내역을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () =>
                    ref.read(ordersControllerProvider.notifier).refresh(),
              ),
        data: (orders) => orders.isEmpty
            ? const AssenEmptyState(
                title: '주문 내역이 없어요',
                message: '아직 주문한 상품이 없습니다.',
              )
            : _OrderList(orders: orders),
      ),
    );
  }
}

/// The loaded history: a list of order cards, newest first.
class _OrderList extends StatelessWidget {
  const _OrderList({required this.orders});

  final List<Order> orders;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: orders.length,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s3),
      itemBuilder: (context, index) =>
          _OrderCard(order: orders[index], now: now),
    );
  }
}

/// One order: a status badge + time header over its summary, total and any
/// refund badge.
class _OrderCard extends StatelessWidget {
  const _OrderCard({required this.order, required this.now});

  final Order order;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final refund = order.refund;

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AssenStatusBadge(
                kind: _statusKind(order.status),
                label: order.statusLabel,
              ),
              const Spacer(),
              Text(
                relativeTime(order.createdAt, now),
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink500,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s3),
          Text(
            order.summary,
            style: TextStyle(
              fontSize: TypographyTokens.titleMSize,
              fontWeight: FontWeight.w600,
              color: colors.ink900,
            ),
          ),
          const SizedBox(height: SpacingTokens.s2),
          Row(
            children: [
              Text(
                '${order.items.length}개 상품',
                style: TextStyle(
                  fontSize: TypographyTokens.bodySSize,
                  color: colors.ink500,
                ),
              ),
              const Spacer(),
              Text(
                order.totalLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
            ],
          ),
          if (refund != null) ...[
            const SizedBox(height: SpacingTokens.s3),
            Align(
              alignment: Alignment.centerLeft,
              child: AssenBadge(
                label: refund.refundLabel,
                hue: _refundHue(refund.status),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Maps an order status to the semantic badge hue.
///
/// `completed` reads as success (matcha), `shipping` as in-progress (lemon),
/// `cancelled`/`refunded` as cancelled (red); everything else (`paid`,
/// `refunding`, an unknown status) is the neutral done (sky) hue.
AssenStatusKind _statusKind(String status) => switch (status) {
  'completed' => AssenStatusKind.confirmed,
  'shipping' => AssenStatusKind.pending,
  'cancelled' || 'refunded' => AssenStatusKind.cancelled,
  _ => AssenStatusKind.done,
};

/// Maps a refund status to the pastel badge hue (no red — pastels are the
/// badge palette; a rejected refund uses peach, the calm caution hue).
AssenBadgeHue _refundHue(String status) => switch (status) {
  'accepted' => AssenBadgeHue.matcha,
  'rejected' => AssenBadgeHue.peach,
  'reviewing' => AssenBadgeHue.lemon,
  _ => AssenBadgeHue.sky,
};

/// The loading state: skeleton order cards standing in for the history.
class _OrdersSkeleton extends StatelessWidget {
  const _OrdersSkeleton();

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
            Row(
              children: [
                AssenSkeleton(width: 64, height: 20),
                Spacer(),
                AssenSkeleton(width: 48),
              ],
            ),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: 180),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: 100),
          ],
        ),
      ),
    );
  }
}
