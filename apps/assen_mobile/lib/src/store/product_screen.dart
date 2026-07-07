import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_controller.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The product detail screen, reached from the store grid via `/product/:id`.
///
/// Wired to `GET /api/products/{id}` through [productControllerProvider]: it
/// renders the async states through ui_kit only — a skeleton while loading, a
/// dedicated "없는 상품" state on 404 ([ProductNotFoundException]) and
/// [AssenErrorState] (with retry) otherwise. On success it shows a
/// *browse-only*
/// detail: media, title, price, description and options, plus sold-out / locked
/// / 19+ badges. There is deliberately no purchase CTA — checkout is a payment
/// gate (IAP) not built on mobile yet; a notice states the browse-only intent.
class ProductScreen extends ConsumerWidget {
  /// Creates the detail screen for the product identified by [productId].
  const ProductScreen({required this.productId, super.key});

  /// The product id from the route path parameter.
  final String productId;

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.store);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(productControllerProvider(productId));
    return Scaffold(
      appBar: AssenAppBar(title: '상품', onBack: () => _back(context)),
      body: detail.when(
        loading: () => const _ProductSkeleton(),
        error: (error, stackTrace) => error is ProductNotFoundException
            ? AssenErrorState(
                title: '없는 상품이에요',
                message: '상품을 찾지 못했어요. 다시 확인해 주세요.',
                retryLabel: '스토어로',
                onRetry: () => context.go(RoutePaths.store),
              )
            : AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () => ref
                    .read(productControllerProvider(productId).notifier)
                    .refresh(),
              ),
        data: (product) => _ProductDetail(product: product),
      ),
    );
  }
}

/// The loaded detail: media, badges, title, price, description and options.
class _ProductDetail extends StatelessWidget {
  const _ProductDetail({required this.product});

  final Product product;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return ListView(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s8),
      children: [
        AspectRatio(
          aspectRatio: 5 / 3,
          child: ColoredBox(
            color: colors.cream200,
            child: product.mediaUrl == null
                ? null
                : Image.network(
                    product.mediaUrl!,
                    fit: BoxFit.cover,
                    // The enclosing cream ColoredBox is the load-failure
                    // placeholder, so suppress Flutter's default error box.
                    errorBuilder: (_, _, _) => const SizedBox.shrink(),
                  ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(SpacingTokens.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Badges(product: product),
              const SizedBox(height: SpacingTokens.s3),
              Text(
                product.title,
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                product.priceLabel,
                style: TextStyle(
                  fontSize: TypographyTokens.titleLSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              if (product.meta != null) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  product.meta!,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
              if (product.stock != null) ...[
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  '재고 ${formatThousands(product.stock!)}개',
                  style: TextStyle(
                    fontSize: TypographyTokens.bodySSize,
                    color: colors.ink500,
                  ),
                ),
              ],
              if (product.description.isNotEmpty) ...[
                const SizedBox(height: SpacingTokens.s5),
                Text(
                  product.description,
                  style: TextStyle(
                    fontSize: TypographyTokens.bodyMSize,
                    height: 1.5,
                    color: colors.ink700,
                  ),
                ),
              ],
              if (product.options.isNotEmpty) ...[
                const SizedBox(height: SpacingTokens.s5),
                const AssenSectionHeader(title: '옵션'),
                const SizedBox(height: SpacingTokens.s2),
                Wrap(
                  spacing: SpacingTokens.s2,
                  runSpacing: SpacingTokens.s2,
                  children: [
                    for (final option in product.options)
                      AssenBadge(label: option, hue: AssenBadgeHue.lavender),
                  ],
                ),
              ],
              const SizedBox(height: SpacingTokens.s6),
              // Browse-only: no purchase CTA — checkout is a payment gate (IAP)
              // not built on mobile yet.
              const AssenNoticeBar(
                message: '지금은 상품을 둘러볼 수 있어요. 구매 기능은 준비 중입니다.',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// The status badge row: tag, sold-out, locked and 19+ markers.
class _Badges extends StatelessWidget {
  const _Badges({required this.product});

  final Product product;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: SpacingTokens.s2,
      runSpacing: SpacingTokens.s2,
      children: [
        if (product.type.isNotEmpty) AssenBadge(label: product.typeLabel),
        if (product.soldOut)
          const AssenStatusBadge(kind: AssenStatusKind.cancelled, label: '품절'),
        if (product.locked)
          const AssenBadge(label: '멤버십 전용', hue: AssenBadgeHue.lavender),
        if (product.isAdult)
          const AssenBadge(label: '19+', hue: AssenBadgeHue.peach),
      ],
    );
  }
}

/// The loading state: a media/title/price skeleton standing in for the detail.
class _ProductSkeleton extends StatelessWidget {
  const _ProductSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: const [
        AspectRatio(
          aspectRatio: 5 / 3,
          child: AssenSkeleton(
            width: double.infinity,
            height: double.infinity,
            radius: 0,
          ),
        ),
        Padding(
          padding: EdgeInsets.all(SpacingTokens.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AssenSkeleton(width: 200, height: 24),
              SizedBox(height: SpacingTokens.s3),
              AssenSkeleton(width: 120, height: 20),
              SizedBox(height: SpacingTokens.s5),
              AssenSkeleton(width: double.infinity),
              SizedBox(height: SpacingTokens.s2),
              AssenSkeleton(width: double.infinity),
            ],
          ),
        ),
      ],
    );
  }
}
