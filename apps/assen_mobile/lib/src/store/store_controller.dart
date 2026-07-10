import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives the store (catalog) grid's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value,
/// and can re-run the fetch via [refresh] (retry) without the screen owning any
/// request state.
class StoreController extends AsyncNotifier<List<Product>>
    with RefreshableAsyncNotifier<List<Product>> {
  @override
  Future<List<Product>> build() {
    return ref.watch(storeRepositoryProvider).fetchProducts();
  }

  @override
  Future<List<Product>> fetch() =>
      ref.read(storeRepositoryProvider).fetchProducts();
}

/// Exposes the store catalog [AsyncValue] and its [StoreController].
final storeControllerProvider =
    AsyncNotifierProvider<StoreController, List<Product>>(
      StoreController.new,
      retry: noRetry,
    );

/// Drives one product detail's async lifecycle, keyed by product id.
///
/// A family [AsyncNotifier] (one instance per id) so each detail renders
/// loading/error/data from a single value and can re-run its fetch via
/// [refresh] (retry). The id argument is delivered to the notifier by the
/// family (Riverpod 3.x) and read back in [build].
class ProductController extends AsyncNotifier<Product>
    with RefreshableAsyncNotifier<Product> {
  /// Creates a controller for the product identified by [productId].
  ProductController(this.productId);

  /// The product id whose detail this controller loads.
  final String productId;

  @override
  Future<Product> build() {
    return ref.watch(storeRepositoryProvider).fetchProduct(productId);
  }

  @override
  Future<Product> fetch() =>
      ref.read(storeRepositoryProvider).fetchProduct(productId);
}

/// Exposes each product detail's [AsyncValue], keyed by product id.
final AsyncNotifierProviderFamily<ProductController, Product, String>
productControllerProvider =
    AsyncNotifierProvider.family<ProductController, Product, String>(
      ProductController.new,
      retry: noRetry,
    );
