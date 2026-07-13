import 'package:assen_mobile/src/checkout/checkout_repository.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `FutureProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show FutureProviderFamily;

/// Loads the product being checked out, keyed by product id.
///
/// Reuses the store repository's single-product fetch so checkout is
/// deep-linkable (it re-resolves the product from the id rather than depending
/// on a value passed through navigation). A 404 surfaces as the store's
/// [ProductNotFoundException], which the 결제 screen maps to a "없는 상품" state.
final FutureProviderFamily<Product, String> checkoutProductProvider =
    FutureProvider.family<Product, String>(
      (ref, productId) =>
          ref.watch(storeRepositoryProvider).fetchProduct(productId),
    );

/// Whether the (mock) payment rail is open — gates the pay action.
///
/// Read from `GET /api/capabilities`; when false the 결제 screen hides the pay
/// button behind a "준비 중" notice (fail-closed) instead of letting a doomed
/// POST reach the server's head-guard.
final paymentAvailableProvider = FutureProvider<bool>(
  (ref) => ref.watch(checkoutRepositoryProvider).paymentAvailable(),
);
