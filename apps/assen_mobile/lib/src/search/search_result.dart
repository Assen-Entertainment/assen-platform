import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/store/product.dart';
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
  /// The envelope contract requires both the `creators` and `products` arrays:
  /// an empty array is the no-results state, but a *missing* key is a contract
  /// violation and throws (an [ArgumentError] via [requireList]) so a backend
  /// field-name drift surfaces as a load error rather than a silently
  /// half-empty result. (The discovery repository stays deliberately lenient —
  /// R7 — so only the newer search/notifications envelopes are strict here.)
  factory SearchResult.fromJson(Map<String, dynamic> json) {
    final creators = requireList(json, 'creators');
    final products = requireList(json, 'products');
    return SearchResult(
      creators: creators
          .map((item) => Creator.fromJson(item as Map<String, dynamic>))
          .toList(),
      products: products
          .map((item) => Product.fromBrief(item as Map<String, dynamic>))
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
