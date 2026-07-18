import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// The creator owner's studio dashboard counts shown on the 스튜디오 screen.
///
/// The app-side view model for the backend `StudioStatsOut` shape
/// (`GET /api/studio/stats`). Every field is a pure count scoped to the caller's
/// own creator — there is NO revenue/settlement figure by design (money is a
/// separate gate). When the generated `api_client` DTOs (P6) land they replace
/// this parsing.
@immutable
class StudioStats {
  /// Creates a studio dashboard summary.
  const StudioStats({
    required this.followers,
    required this.posts,
    required this.products,
    required this.productsSelling,
    required this.orders,
    required this.subscribers,
  });

  /// Builds a [StudioStats] from a backend `StudioStatsOut` JSON object.
  ///
  /// Every field — `followers`, `posts`, `products`, `products_selling`,
  /// `orders`, `subscribers` — is contract-required and parsed strictly with
  /// [requireInt]: a missing key or non-numeric value throws [ArgumentError] so
  /// a backend field drift surfaces as a load error rather than a silent `0`.
  factory StudioStats.fromJson(Map<String, dynamic> json) {
    return StudioStats(
      followers: requireInt(json, 'followers'),
      posts: requireInt(json, 'posts'),
      products: requireInt(json, 'products'),
      productsSelling: requireInt(json, 'products_selling'),
      orders: requireInt(json, 'orders'),
      subscribers: requireInt(json, 'subscribers'),
    );
  }

  /// Fans following the creator (server `followers`).
  final int followers;

  /// The creator's feed posts (server `posts`).
  final int posts;

  /// Catalog products the creator owns, all statuses (server `products`).
  final int products;

  /// The subset currently on public sale (server `products_selling`).
  final int productsSelling;

  /// Distinct non-cancelled orders containing the creator's products (server
  /// `orders`); a count, never an amount.
  final int orders;

  /// The creator's active subscribers (server `subscribers`).
  final int subscribers;
}
