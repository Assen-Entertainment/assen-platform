import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/products/{id}` returns 404 (unknown/not visible).
///
/// A typed marker (not a generic error) so the product detail screen can render
/// the dedicated "없는 상품" state instead of the generic retry error. The server
/// 404s a draft/hidden/gated item just like an unknown id (no existence leak),
/// so this covers both.
class ProductNotFoundException implements Exception {
  /// Creates the not-found marker for [productId].
  const ProductNotFoundException(this.productId);

  /// The product id that did not resolve.
  final String productId;

  @override
  String toString() => 'ProductNotFoundException($productId)';
}

/// Fetches the public store catalog from the backend.
///
/// A thin repository over [Dio] owning the endpoint paths and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class StoreRepository {
  /// Creates a repository backed by [_dio].
  const StoreRepository(this._dio);

  final Dio _dio;

  /// Loads the global product catalog via `GET /api/products`.
  ///
  /// Maps the `ProductPage` envelope (`{items, next_cursor}`) into a list of
  /// [Product]s; only the first page is read here (cursor paging is a
  /// follow-up).
  /// The envelope is parsed strictly: the `items` array must be present
  /// (an empty
  /// array is the empty catalog), but a *missing* key is a contract
  /// violation and
  /// throws (an [ArgumentError] via [requireList]) rather than silently showing
  /// an empty store — matching the search/notifications envelopes.
  Future<List<Product>> fetchProducts() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/products');
    final body = response.data ?? const <String, dynamic>{};
    final items = requireList(body, 'items');
    return items
        .map((item) => Product.fromDetail(item as Map<String, dynamic>))
        .toList();
  }

  /// Loads a single catalog product via `GET /api/products/{id}`.
  ///
  /// A 404 is translated into a [ProductNotFoundException] so the screen shows
  /// the "unknown product" state; other transport errors propagate to the
  /// generic error state.
  Future<Product> fetchProduct(String productId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/products/${Uri.encodeComponent(productId)}',
      );
      return Product.fromDetail(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw ProductNotFoundException(productId);
      }
      rethrow;
    }
  }
}

/// Provides the [StoreRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the store screens can render mock
/// data without a network.
final storeRepositoryProvider = Provider<StoreRepository>(
  (ref) => StoreRepository(ref.watch(dioProvider)),
);
