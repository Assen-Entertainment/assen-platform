import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/cached_media.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_controller.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The global store: the public product catalog (`GET /api/products`).
///
/// Reached from the discovery home shortcut. Wired to
/// [storeControllerProvider]: it renders the three async states through ui_kit
/// only — a grid of card skeletons while loading, [AssenErrorState] (with
/// retry) on failure, an [AssenEmptyState] for an empty catalog, and
/// otherwise a
/// responsive grid of [AssenProductCard]s. Tapping a card opens the browse-only
/// product detail (no purchase here — checkout is a payment gate).
class StoreScreen extends ConsumerWidget {
  /// Creates the store screen.
  const StoreScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.discovery);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final catalog = ref.watch(storeControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '스토어', onBack: () => _back(context)),
      body: AssenAsyncView<List<Product>>(
        value: catalog,
        loading: const _StoreSkeleton(),
        onRetry: () => ref.read(storeControllerProvider.notifier).refresh(),
        isEmpty: (products) => products.isEmpty,
        empty: () => AssenEmptyState(
          title: '아직 상품이 없어요',
          message: '곧 새로운 상품이 이곳에 소개됩니다.',
          actionLabel: '새로고침',
          onAction: () => ref.read(storeControllerProvider.notifier).refresh(),
        ),
        data: (products) => RefreshIndicator(
          onRefresh: () => ref.read(storeControllerProvider.notifier).refresh(),
          child: _ProductGrid(products: products),
        ),
      ),
    );
  }
}

/// The loaded catalog: a responsive, viewport-culled grid of product cards.
///
/// A [GridView.builder] (lazy sliver) rather than a `SingleChildScrollView`
/// over an eager [AssenFeedGrid], so only the cards near the viewport are
/// built — the catalog scrolls a large product list without laying every card
/// out up front. Columns derive from the pane width (max ~220dp each, so two
/// columns on a phone); `mainAxisExtent` fixes the cell height to the card's
/// media (5:3) + single-line text block. Wrapped by a `RefreshIndicator`, so
/// `AlwaysScrollableScrollPhysics` keeps pull-to-refresh working for a short
/// catalog that does not fill the viewport.
class _ProductGrid extends StatelessWidget {
  const _ProductGrid({required this.products});

  final List<Product> products;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      physics: const AlwaysScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 220,
        mainAxisExtent: 268,
        crossAxisSpacing: SpacingTokens.s3,
        mainAxisSpacing: SpacingTokens.s4,
      ),
      itemCount: products.length,
      itemBuilder: (context, index) {
        final product = products[index];
        return AssenProductCard(
          title: product.title,
          priceLabel: product.priceLabel,
          tagLabel: product.typeLabel,
          meta: product.meta,
          media: product.mediaUrl == null
              ? null
              : CachedMedia(
                  url: product.mediaUrl!,
                  semanticLabel: product.title,
                ),
          onTap: () => context.go(RoutePaths.product(product.id)),
        );
      },
    );
  }
}

/// The loading state: a grid of card-shaped skeletons.
class _StoreSkeleton extends StatelessWidget {
  const _StoreSkeleton();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      child: AssenFeedGrid(
        minColumnWidth: 160,
        maxColumns: 2,
        columnSpacing: SpacingTokens.s3,
        rowSpacing: SpacingTokens.s4,
        children: List.generate(
          6,
          (_) => const Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AspectRatio(
                aspectRatio: 5 / 3,
                child: AssenSkeleton(
                  width: double.infinity,
                  height: double.infinity,
                  radius: RadiusTokens.lg,
                ),
              ),
              SizedBox(height: SpacingTokens.s2),
              AssenSkeleton(width: 120),
              SizedBox(height: SpacingTokens.s2),
              AssenSkeleton(width: 80),
            ],
          ),
        ),
      ),
    );
  }
}
