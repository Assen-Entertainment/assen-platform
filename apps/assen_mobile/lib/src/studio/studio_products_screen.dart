import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/studio/studio_product.dart';
import 'package:assen_mobile/src/studio/studio_products_controller.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 상품 관리 (studio products) screen: the creator owner's catalog.
///
/// Wired to `GET /api/studio/products` through its controller. Two unauthorised
/// states, as on the studio dashboard: a 401 renders "로그인이 필요해요", a 403
/// (signed-in non-owner) the "크리에이터 전용" notice. Each row shows the product's
/// title, price, status and units sold (a count, not revenue). Read-only.
class StudioProductsScreen extends ConsumerWidget {
  /// Creates the studio products screen.
  const StudioProductsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.studio);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final products = ref.watch(studioProductsControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '상품 관리', onBack: () => _back(context)),
      body: AssenAsyncView<List<StudioProduct>>(
        value: products,
        loading: const _StudioListSkeleton(),
        onRetry: () =>
            ref.read(studioProductsControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => switch (error) {
          StudioAuthRequiredException() => AssenEmptyState(
            title: '로그인이 필요해요',
            message: '상품을 관리하려면 먼저 로그인해 주세요.',
            actionLabel: '로그인',
            onAction: () => context.go(RoutePaths.login),
          ),
          StudioOwnerRequiredException() => const AssenEmptyState(
            title: '크리에이터 전용이에요',
            message: '상품 관리는 크리에이터 계정에서만 볼 수 있어요.',
          ),
          _ => null,
        },
        isEmpty: (items) => items.isEmpty,
        empty: () => const AssenEmptyState(
          title: '등록한 상품이 없어요',
          message: '스토어에 상품을 등록하면 여기에서 관리할 수 있어요.',
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(studioProductsControllerProvider.notifier).refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            itemCount: items.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: SpacingTokens.s3),
            itemBuilder: (context, index) =>
                _ProductCard(product: items[index]),
          ),
        ),
      ),
    );
  }
}

/// One catalog product: title + meta over price, status and sold count.
class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product});

  final StudioProduct product;

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
                  product.title,
                  style: TextStyle(
                    fontSize: TypographyTokens.titleMSize,
                    fontWeight: FontWeight.w600,
                    color: colors.ink900,
                  ),
                ),
              ),
              AssenStatusBadge(
                kind: product.soldOut
                    ? AssenStatusKind.cancelled
                    : AssenStatusKind.done,
                label: product.soldOut ? '품절' : product.statusLabel,
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s2),
          Row(
            children: [
              Text(
                product.priceLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              const Spacer(),
              Text(
                '판매 ${product.sold}',
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

/// The loading state: skeleton management cards, reused across studio lists.
class _StudioListSkeleton extends StatelessWidget {
  const _StudioListSkeleton();

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
            AssenSkeleton(width: 160),
            SizedBox(height: SpacingTokens.s3),
            AssenSkeleton(width: 100),
          ],
        ),
      ),
    );
  }
}
