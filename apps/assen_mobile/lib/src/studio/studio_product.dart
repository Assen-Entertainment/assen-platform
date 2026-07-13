import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// One of the signed-in creator's catalog products, owner view.
///
/// The app-side view model for the backend `StudioProductOut` shape
/// (`GET /api/studio/products`). Adds the management fields the fan-facing
/// product view omits — [status], [sold], [isAdult]. [sold] is a count of
/// non-cancelled orders (ASS-264), never a settlement/revenue figure (money is a
/// separate gate). When the generated `api_client` DTOs (P6) land they replace
/// this parsing.
@immutable
class StudioProduct {
  /// Creates a studio (owner-view) product.
  const StudioProduct({
    required this.id,
    required this.type,
    required this.title,
    required this.price,
    required this.status,
    required this.soldOut,
    required this.sold,
    required this.isAdult,
    this.meta = '',
    this.stock,
  });

  /// Builds a [StudioProduct] from a `StudioProductOut` JSON object.
  ///
  /// The contract-required fields — `id`, `type`, `title`, `price`, `status`,
  /// `sold` — are parsed strictly; the display/flag fields degrade to their
  /// fail-closed defaults so a partial payload renders a safe row.
  factory StudioProduct.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError('studio product payload is missing a required "id"');
    }
    return StudioProduct(
      id: rawId.toString(),
      type: requireString(json, 'type'),
      title: requireString(json, 'title'),
      price: requireInt(json, 'price'),
      meta: json['meta'] as String? ?? '',
      status: requireString(json, 'status'),
      soldOut: json['sold_out'] as bool? ?? false,
      sold: requireInt(json, 'sold'),
      isAdult: json['is_adult'] as bool? ?? false,
      stock: json['stock'] as int?,
    );
  }

  /// The product's stable id (server `id`).
  final String id;

  /// The product type (server `type`, e.g. `goods`/`ticket`).
  final String type;

  /// The product title (server `title`).
  final String title;

  /// The display price in KRW won (server `price`).
  final int price;

  /// A short meta/option line (server `meta`); empty when none.
  final String meta;

  /// The management status (server `status`, e.g. `selling`/`draft`/`hidden`).
  final String status;

  /// Whether the product is flagged sold-out (server `sold_out`).
  final bool soldOut;

  /// Units sold via non-cancelled orders (server `sold`); a count, not revenue.
  final int sold;

  /// Whether the product is 19+ (server `is_adult`).
  final bool isAdult;

  /// Remaining stock (server `stock`); null when the product is not stocked.
  final int? stock;

  /// The price formatted as `₩12,000`.
  String get priceLabel => '₩${formatThousands(price)}';

  /// The Korean label for [status] (falls back to the raw value if unknown).
  String get statusLabel => switch (status) {
    'selling' => '판매중',
    'draft' => '임시저장',
    'hidden' => '숨김',
    'sold_out' => '품절',
    _ => status,
  };
}
