import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches search results (creators + products) from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class SearchRepository {
  /// Creates a repository backed by [_dio].
  const SearchRepository(this._dio);

  final Dio _dio;

  /// Runs a public search for [query] via `GET /api/search?q=`.
  ///
  /// Maps the `SearchOut` envelope (`{creators, products}`) into a
  /// [SearchResult]. The caller is expected to pass a non-empty, trimmed query;
  /// the server returns empty lists for a blank term either way.
  Future<SearchResult> search(String query) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/search',
      queryParameters: {'q': query},
    );
    return SearchResult.fromJson(response.data ?? const <String, dynamic>{});
  }
}

/// Provides the [SearchRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the search screen can render mock
/// results without a network.
final searchRepositoryProvider = Provider<SearchRepository>(
  (ref) => SearchRepository(ref.watch(dioProvider)),
);
