import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/studio/studio_product.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches the creator owner's own catalog products (management view).
///
/// A thin repository over [Dio] owning `GET /api/studio/products` and the
/// JSON→model mapping. Reuses the studio auth markers: a 401 becomes a
/// [StudioAuthRequiredException] (signed out) and a 403 a
/// [StudioOwnerRequiredException] (signed-in non-owner). Read-only —
/// create/edit/delete are follow-up work. When the generated `api_client` (P6)
/// lands this delegates to it instead of Dio.
class StudioProductsRepository {
  /// Creates a repository backed by [_dio].
  const StudioProductsRepository(this._dio);

  final Dio _dio;

  /// Loads the owner's products via `GET /api/studio/products` (owner auth).
  ///
  /// The endpoint returns a *bare* JSON array (`list[StudioProductOut]`). A
  /// `null`/non-array body is a contract violation and throws; only a real empty
  /// array `[]` means the creator has no products.
  Future<List<StudioProduct>> fetchProducts() async {
    try {
      final response = await _dio.get<dynamic>('/api/studio/products');
      final data = response.data;
      if (data is! List) {
        throw ArgumentError(
          'GET /api/studio/products must return a JSON array '
          '(list[StudioProductOut])',
        );
      }
      return data
          .map((item) => StudioProduct.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401) throw const StudioAuthRequiredException();
      if (status == 403) throw const StudioOwnerRequiredException();
      rethrow;
    }
  }
}

/// Provides the [StudioProductsRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 상품 관리 screen can render mock
/// products (or the 401/403 branches) without a network.
final studioProductsRepositoryProvider = Provider<StudioProductsRepository>(
  (ref) => StudioProductsRepository(ref.watch(dioProvider)),
);
