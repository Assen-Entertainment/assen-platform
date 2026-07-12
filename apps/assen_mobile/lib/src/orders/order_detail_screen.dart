import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/common/now.dart';
import 'package:assen_mobile/src/common/relative_time.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/order_detail_controller.dart';
import 'package:assen_mobile/src/orders/order_detail_repository.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 주문 상세 (order detail) screen: one order's full breakdown for its owner.
///
/// Wired to `GET /api/orders/{id}` through [orderDetailControllerProvider]
/// (keyed by id). Shows the status, contents, price summary, and — for a goods
/// order — the delivery snapshot (recipient/phone/postal/street), which the
/// orders list deliberately omits (ASS-291 A-3). A 401 renders "로그인이 필요해요";
/// a 404 renders "주문을 찾을 수 없어요"; other failures fall back to
/// [AssenErrorState] with retry. Read-only — cancel/refund are payment gates.
class OrderDetailScreen extends ConsumerWidget {
  /// Creates the order-detail screen for [orderId].
  const OrderDetailScreen({required this.orderId, super.key});

  /// The id of the order to show.
  final String orderId;

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.orders);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final order = ref.watch(orderDetailControllerProvider(orderId));
    final now = ref.watch(nowProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '주문 상세', onBack: () => _back(context)),
      body: AssenAsyncView<Order>(
        value: order,
        loading: const _DetailSkeleton(),
        onRetry: () => ref
            .read(orderDetailControllerProvider(orderId).notifier)
            .refresh(),
        errorBuilder: (error, _) {
          if (error is OrdersAuthRequiredException) {
            return AssenEmptyState(
              title: '로그인이 필요해요',
              message: '주문 상세를 보려면 먼저 로그인해 주세요.',
              actionLabel: '로그인',
              onAction: () => context.go(RoutePaths.login),
            );
          }
          if (error is OrderNotFoundException) {
            return const AssenEmptyState(
              title: '주문을 찾을 수 없어요',
              message: '이미 삭제되었거나 접근할 수 없는 주문이에요.',
            );
          }
          return null;
        },
        data: (value) => _OrderDetailBody(order: value, now: now),
      ),
    );
  }
}

/// The loaded detail: status header, contents, price summary, delivery, refund.
class _OrderDetailBody extends StatelessWidget {
  const _OrderDetailBody({required this.order, required this.now});

  final Order order;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final refund = order.refund;
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
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
        const SizedBox(height: SpacingTokens.s2),
        Text(
          '주문번호 ${order.id}',
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            color: colors.ink500,
          ),
        ),
        const SizedBox(height: SpacingTokens.s5),

        const AssenSectionHeader(title: '주문 상품'),
        AssenCard(
          child: Column(
            children: [
              for (var i = 0; i < order.items.length; i++) ...[
                if (i > 0) const SizedBox(height: SpacingTokens.s3),
                _ItemRow(item: order.items[i]),
              ],
            ],
          ),
        ),
        const SizedBox(height: SpacingTokens.s5),

        const AssenSectionHeader(title: '결제 정보'),
        AssenCard(
          child: Column(
            children: [
              _SummaryRow(
                label: '상품 금액',
                value: '₩${formatThousands(order.subtotal)}',
              ),
              const SizedBox(height: SpacingTokens.s2),
              _SummaryRow(
                label: '배송비',
                value: '₩${formatThousands(order.shippingFee)}',
              ),
              const SizedBox(height: SpacingTokens.s3),
              const AssenDivider(),
              const SizedBox(height: SpacingTokens.s3),
              _SummaryRow(
                label: '총 결제 금액',
                value: order.totalLabel,
                emphasize: true,
              ),
            ],
          ),
        ),

        if (order.shippingAddress != null) ...[
          const SizedBox(height: SpacingTokens.s5),
          const AssenSectionHeader(title: '배송지'),
          _ShippingCard(shipping: order.shippingAddress!),
        ],

        if (refund != null) ...[
          const SizedBox(height: SpacingTokens.s5),
          const AssenSectionHeader(title: '환불'),
          AssenCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AssenBadge(
                  label: refund.refundLabel,
                  hue: _refundHue(refund.status),
                ),
                if (refund.reason.isNotEmpty) ...[
                  const SizedBox(height: SpacingTokens.s3),
                  Text(
                    refund.reason,
                    style: TextStyle(
                      fontSize: TypographyTokens.bodyMSize,
                      color: colors.ink600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// One purchased line: title + option over unit price × qty.
class _ItemRow extends StatelessWidget {
  const _ItemRow({required this.item});

  final OrderItem item;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.title,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w600,
                  color: colors.ink900,
                ),
              ),
              if (item.option.isNotEmpty) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  item.option,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(width: SpacingTokens.s3),
        Text(
          '₩${formatThousands(item.price)} × ${item.qty}',
          style: TextStyle(
            fontSize: TypographyTokens.bodyMSize,
            color: colors.ink900,
          ),
        ),
      ],
    );
  }
}

/// One label→value row in the price summary; [emphasize] bolds the total.
class _SummaryRow extends StatelessWidget {
  const _SummaryRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final size = emphasize
        ? TypographyTokens.titleMSize
        : TypographyTokens.bodyMSize;
    final weight = emphasize ? FontWeight.w700 : FontWeight.w400;
    return Row(
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: size,
            fontWeight: weight,
            color: emphasize ? colors.ink900 : colors.ink600,
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: TextStyle(
            fontSize: size,
            fontWeight: weight,
            color: colors.ink900,
          ),
        ),
      ],
    );
  }
}

/// The delivery snapshot card (owner-only PII, display-only).
class _ShippingCard extends StatelessWidget {
  const _ShippingCard({required this.shipping});

  final OrderShipping shipping;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final street = [
      shipping.address1,
      shipping.address2,
    ].where((s) => s.isNotEmpty).join(' ');
    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${shipping.recipientName} · ${shipping.recipientPhone}',
            style: TextStyle(
              fontSize: TypographyTokens.titleMSize,
              fontWeight: FontWeight.w600,
              color: colors.ink900,
            ),
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            '(${shipping.postalCode}) $street',
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Maps an order status to the semantic badge hue (mirrors the orders list).
AssenStatusKind _statusKind(String status) => switch (status) {
  'completed' => AssenStatusKind.confirmed,
  'shipping' => AssenStatusKind.pending,
  'cancelled' || 'refunded' => AssenStatusKind.cancelled,
  _ => AssenStatusKind.done,
};

/// Maps a refund status to the pastel badge hue (mirrors the orders list).
AssenBadgeHue _refundHue(String status) => switch (status) {
  'accepted' => AssenBadgeHue.matcha,
  'rejected' => AssenBadgeHue.peach,
  'reviewing' => AssenBadgeHue.lemon,
  _ => AssenBadgeHue.sky,
};

/// The loading state: a skeleton status header over card placeholders.
class _DetailSkeleton extends StatelessWidget {
  const _DetailSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenSkeleton(width: 80, height: 24),
          SizedBox(height: SpacingTokens.s4),
          AssenSkeleton(width: double.infinity, height: 96),
          SizedBox(height: SpacingTokens.s4),
          AssenSkeleton(width: double.infinity, height: 120),
        ],
      ),
    );
  }
}
