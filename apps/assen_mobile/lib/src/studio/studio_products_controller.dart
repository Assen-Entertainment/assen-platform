import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/studio/studio_product.dart';
import 'package:assen_mobile/src/studio/studio_products_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 상품 관리 (studio products) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a StudioAuthRequiredException, a signed-in non-owner as a
/// StudioOwnerRequiredException, which the screen maps to its two states.
class StudioProductsController extends AsyncNotifier<List<StudioProduct>>
    with RefreshableAsyncNotifier<List<StudioProduct>> {
  @override
  Future<List<StudioProduct>> build() =>
      ref.watch(studioProductsRepositoryProvider).fetchProducts();

  @override
  Future<List<StudioProduct>> fetch() =>
      ref.read(studioProductsRepositoryProvider).fetchProducts();
}

/// Exposes the owner's products [AsyncValue] and its controller.
final studioProductsControllerProvider =
    AsyncNotifierProvider<StudioProductsController, List<StudioProduct>>(
      StudioProductsController.new,
      retry: noRetry,
    );
