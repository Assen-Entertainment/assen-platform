import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/search/product.dart';
import 'package:flutter/foundation.dart';

/// The parsed result of a `GET /api/search` call: matching creators + products.
///
/// The app-side view model for the backend `SearchOut` envelope
/// (`{creators:[CreatorOut], products:[ProductBrief]}`). Either list may be
/// empty; [isEmpty] is true only when both are, which the search screen renders
/// as the "no results" empty state.
@immutable
class SearchResult {
  /// Creates a search result from its [creators] and [products].
  const SearchResult({required this.creators, required this.products});

  /// An empty result — both the initial (no query) and cleared states.
  const SearchResult.empty() : creators = const [], products = const [];

  /// Builds a [SearchResult] from a backend `SearchOut` JSON object.
  ///
  /// A missing `creators`/`products` array is treated as an empty list rather
  /// than an error, so a partial payload still renders whichever side arrived.
  factory SearchResult.fromJson(Map<String, dynamic> json) {
    final creators = json['creators'] as List<dynamic>? ?? const <dynamic>[];
    final products = json['products'] as List<dynamic>? ?? const <dynamic>[];
    return SearchResult(
      creators: creators
          .map((item) => Creator.fromJson(item as Map<String, dynamic>))
          .toList(),
      products: products
          .map((item) => Product.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  /// The matching creators (may be empty).
  final List<Creator> creators;

  /// The matching products (may be empty).
  final List<Product> products;

  /// Whether the result holds no matches at all.
  bool get isEmpty => creators.isEmpty && products.isEmpty;
}
